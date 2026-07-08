"""Asynchronous submission evaluation.

Validation stays synchronous inside the upload request; only the slow scoring is
deferred to this module. An in-process worker thread drains a SQLite-backed queue
one submission at a time, so no external broker or extra service is required.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from fastapi import FastAPI

from app.config import Settings
from app.db import connect
from app.evaluation import (
    evaluate_submission,
    evaluate_submission_query_metrics,
    persist_evaluation_results,
)
from app.ground_truth import get_ground_truth_version
from app.submissions import (
    claim_next_queued_submission,
    get_admin_submission_detail,
    mark_submission_status,
    parse_trec_eval,
    requeue_processing_submissions,
)

logger = logging.getLogger(__name__)

IDLE_SLEEP_SECONDS = 1.0


def process_submission(app_settings: Settings, submission_id: int) -> None:
    """Evaluate a single queued submission from its preserved file.

    Re-reads and re-parses the stored file rather than trusting an in-memory
    parse from validation (which is gone by the time the worker runs). This keeps
    evaluation reproducible from the file that was preserved on disk.
    """
    with connect(app_settings.database_path) as connection:
        detail = get_admin_submission_detail(connection, submission_id=submission_id)
        if detail is None:
            return

        mark_submission_status(
            connection,
            submission_id=submission_id,
            status="processing",
        )

        try:
            if not detail.stored_file_path:
                raise RuntimeError("Submission file is missing.")

            text = Path(detail.stored_file_path).read_text(encoding="utf-8-sig")
            parsed = parse_trec_eval(text)

            ground_truth_version = (
                get_ground_truth_version(connection, detail.ground_truth_version_id)
                if detail.ground_truth_version_id is not None
                else None
            )
            if ground_truth_version is None:
                mark_submission_status(
                    connection,
                    submission_id=submission_id,
                    status="evaluation_failed",
                    validation_summary="Evaluation failed: ground truth version is unavailable.",
                )
                return

            metrics = evaluate_submission(
                parsed,
                subtask=detail.subtask,  # type: ignore[arg-type]
                ground_truth_version=ground_truth_version,
            )
            query_metrics = evaluate_submission_query_metrics(
                parsed,
                subtask=detail.subtask,  # type: ignore[arg-type]
                ground_truth_version=ground_truth_version,
            )
            persist_evaluation_results(
                connection,
                submission_id=submission_id,
                ground_truth_version_id=ground_truth_version.id,
                metrics=metrics,
                query_metrics=query_metrics,
            )
        except Exception as exc:  # noqa: BLE001 - any failure must land the submission in a terminal state
            logger.exception("Evaluation failed for submission %s", submission_id)
            mark_submission_status(
                connection,
                submission_id=submission_id,
                status="evaluation_failed",
                validation_summary=f"Evaluation failed: {exc}",
            )


class EvaluationWorker(threading.Thread):
    """Background thread that claims and evaluates queued submissions in order."""

    def __init__(
        self,
        app_settings: Settings,
        *,
        idle_sleep_seconds: float = IDLE_SLEEP_SECONDS,
    ) -> None:
        super().__init__(name="evaluation-worker", daemon=True)
        self._app_settings = app_settings
        self._idle_sleep_seconds = idle_sleep_seconds
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            submission_id = self._claim_next()
            if submission_id is None:
                self._stop_event.wait(self._idle_sleep_seconds)
                continue
            process_submission(self._app_settings, submission_id)

    def _claim_next(self) -> int | None:
        with connect(self._app_settings.database_path) as connection:
            return claim_next_queued_submission(connection)


def recover_orphaned_submissions(app_settings: Settings) -> int:
    """Re-queue submissions left ``processing`` by an interrupted worker."""
    with connect(app_settings.database_path) as connection:
        return requeue_processing_submissions(connection)


def run_pending_evaluations(app_settings: Settings) -> int:
    """Drain the queue synchronously. Used by eager mode and tests."""
    processed = 0
    while True:
        with connect(app_settings.database_path) as connection:
            submission_id = claim_next_queued_submission(connection)
        if submission_id is None:
            break
        process_submission(app_settings, submission_id)
        processed += 1
    return processed


def start_evaluation_worker(app: FastAPI) -> None:
    worker = EvaluationWorker(app.state.settings)
    app.state.evaluation_worker = worker
    worker.start()


def stop_evaluation_worker(app: FastAPI) -> None:
    worker = getattr(app.state, "evaluation_worker", None)
    if worker is None:
        return
    worker.stop()
    worker.join(timeout=5.0)
    app.state.evaluation_worker = None
