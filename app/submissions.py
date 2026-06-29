from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from itertools import groupby
from pathlib import Path

from app.config import Settings
from app.ground_truth import JST, GroundTruthRequirements, jst_now_text, safe_filename, sha256_bytes

MAX_RUNS_PER_SUBTASK = 5
EXPECTED_FIELD_COUNT = 6
ALLOWED_SUBMISSION_SUFFIX = ".txt"


@dataclass(frozen=True)
class SubmissionLine:
    line_number: int
    topic_id: str
    doc_id: str
    rank: int
    score: float
    run_id: str
    source_order: int


@dataclass(frozen=True)
class SubmissionValidationError:
    message: str
    line_number: int | None = None
    field_name: str | None = None
    error_code: str = "invalid_submission"
    severity: str = "error"


@dataclass(frozen=True)
class ParsedSubmission:
    lines: tuple[SubmissionLine, ...]
    errors: tuple[SubmissionValidationError, ...]
    run_ids: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_valid(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class SubmissionValidationResult:
    parsed: ParsedSubmission
    errors: tuple[SubmissionValidationError, ...]
    ground_truth_version_id: int | None = None

    @property
    def is_valid(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class SubmissionPeriod:
    id: int
    name: str
    starts_at_jst: str | None
    deadline_at_jst: str
    is_open_override: bool


@dataclass(frozen=True)
class StoredSubmissionFile:
    path: Path
    sha256: str
    size_bytes: int


def parse_trec_eval(content: str, *, max_runs: int = MAX_RUNS_PER_SUBTASK) -> ParsedSubmission:
    lines: list[SubmissionLine] = []
    errors: list[SubmissionValidationError] = []
    run_ids: set[str] = set()
    source_order = 0

    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue

        fields = stripped.split()
        if len(fields) != EXPECTED_FIELD_COUNT:
            errors.append(
                SubmissionValidationError(
                    line_number=line_number,
                    field_name=None,
                    error_code="field_count",
                    message=f"Expected 6 fields, found {len(fields)}.",
                )
            )
            continue

        topic_id, q0, doc_id, rank_text, score_text, run_id = fields

        if q0 != "Q0":
            errors.append(
                SubmissionValidationError(
                    line_number=line_number,
                    field_name="Q0",
                    error_code="invalid_q0",
                    message="Field 2 must be Q0.",
                )
            )

        try:
            rank = int(rank_text)
        except ValueError:
            errors.append(
                SubmissionValidationError(
                    line_number=line_number,
                    field_name="Rank",
                    error_code="invalid_rank",
                    message="Rank must be a positive integer.",
                )
            )
            continue

        if rank <= 0:
            errors.append(
                SubmissionValidationError(
                    line_number=line_number,
                    field_name="Rank",
                    error_code="invalid_rank",
                    message="Rank must be a positive integer.",
                )
            )

        try:
            score = float(score_text)
        except ValueError:
            errors.append(
                SubmissionValidationError(
                    line_number=line_number,
                    field_name="Score",
                    error_code="invalid_score",
                    message="Score must be numeric.",
                )
            )
            continue

        if not run_id:
            errors.append(
                SubmissionValidationError(
                    line_number=line_number,
                    field_name="RunID",
                    error_code="missing_run_id",
                    message="RunID is required.",
                )
            )
            continue

        run_ids.add(run_id)
        source_order += 1
        lines.append(
            SubmissionLine(
                line_number=line_number,
                topic_id=topic_id,
                doc_id=doc_id,
                rank=rank,
                score=score,
                run_id=run_id,
                source_order=source_order,
            )
        )

    if len(run_ids) > max_runs:
        errors.append(
            SubmissionValidationError(
                error_code="too_many_runs",
                message=f"Submission contains {len(run_ids)} run IDs; maximum is {max_runs}.",
            )
        )

    errors.extend(validate_unique_run_topic_doc(lines))
    errors.extend(validate_score_rank_order(lines))

    return ParsedSubmission(
        lines=tuple(lines),
        errors=tuple(errors),
        run_ids=tuple(sorted(run_ids)),
    )


def validate_unique_run_topic_doc(lines: list[SubmissionLine]) -> list[SubmissionValidationError]:
    errors: list[SubmissionValidationError] = []
    seen: dict[tuple[str, str, str], SubmissionLine] = {}

    for line in lines:
        key = (line.run_id, line.topic_id, line.doc_id)
        previous = seen.get(key)
        if previous is not None:
            errors.append(
                SubmissionValidationError(
                    line_number=line.line_number,
                    error_code="duplicate_run_topic_doc",
                    message=(
                        f"Duplicate RunID/topicID/docID combination also appears on "
                        f"line {previous.line_number}."
                    ),
                )
            )
            continue
        seen[key] = line

    return errors


def validate_score_rank_order(lines: list[SubmissionLine]) -> list[SubmissionValidationError]:
    errors: list[SubmissionValidationError] = []
    grouped_lines = sorted(lines, key=lambda line: (line.run_id, line.topic_id, line.source_order))

    for (run_id, topic_id), group in groupby(
        grouped_lines,
        key=lambda line: (line.run_id, line.topic_id),
    ):
        query_lines = list(group)
        submitted_order = sorted(query_lines, key=lambda line: (line.rank, line.source_order))
        score_order = sorted(query_lines, key=lambda line: (-line.score, line.source_order))

        if [line.doc_id for line in submitted_order] != [line.doc_id for line in score_order]:
            errors.append(
                SubmissionValidationError(
                    line_number=query_lines[0].line_number,
                    field_name="Rank",
                    error_code="rank_score_order_mismatch",
                    message=(
                        f"RunID {run_id} topicID {topic_id} rank order does not match "
                        "score order."
                    ),
                    severity="warning",
                )
            )

    return errors


def validate_query_model_completeness(
    parsed: ParsedSubmission,
    *,
    required_topic_ids: set[str],
    required_doc_ids: set[str],
) -> tuple[SubmissionValidationError, ...]:
    errors: list[SubmissionValidationError] = []

    for line in parsed.lines:
        if line.topic_id not in required_topic_ids:
            errors.append(
                SubmissionValidationError(
                    line_number=line.line_number,
                    field_name="topicID",
                    error_code="unknown_topic_id",
                    message=f"Unknown topicID: {line.topic_id}.",
                )
            )
        if line.doc_id not in required_doc_ids:
            errors.append(
                SubmissionValidationError(
                    line_number=line.line_number,
                    field_name="docID",
                    error_code="unknown_doc_id",
                    message=f"Unknown docID: {line.doc_id}.",
                )
            )

    if errors:
        return tuple(errors)

    lines_by_run: dict[str, list[SubmissionLine]] = {}
    for line in parsed.lines:
        lines_by_run.setdefault(line.run_id, []).append(line)

    for run_id in parsed.run_ids:
        run_lines = lines_by_run.get(run_id, [])
        present_topics = {line.topic_id for line in run_lines}
        missing_topics = sorted(required_topic_ids - present_topics)
        for topic_id in missing_topics:
            errors.append(
                SubmissionValidationError(
                    error_code="missing_topic_id",
                    message=f"RunID {run_id} is missing topicID {topic_id}.",
                )
            )

        for topic_id in sorted(required_topic_ids):
            present_docs = {
                line.doc_id
                for line in run_lines
                if line.topic_id == topic_id
            }
            missing_docs = sorted(required_doc_ids - present_docs)
            for doc_id in missing_docs:
                errors.append(
                    SubmissionValidationError(
                        error_code="missing_doc_id",
                        message=f"RunID {run_id} topicID {topic_id} is missing docID {doc_id}.",
                    )
                )

    return tuple(errors)


def validate_submission_against_requirements(
    content: str,
    requirements: GroundTruthRequirements | None,
) -> SubmissionValidationResult:
    parsed = parse_trec_eval(content)
    errors = list(parsed.errors)

    if requirements is None:
        errors.append(
            SubmissionValidationError(
                error_code="missing_active_ground_truth",
                message="No active ground truth is configured for this subtask.",
            )
        )
        return SubmissionValidationResult(parsed=parsed, errors=tuple(errors))

    if parsed.errors:
        return SubmissionValidationResult(
            parsed=parsed,
            errors=tuple(errors),
            ground_truth_version_id=requirements.ground_truth_version_id,
        )

    errors.extend(
        validate_query_model_completeness(
            parsed,
            required_topic_ids=set(requirements.required_topic_ids),
            required_doc_ids=set(requirements.required_doc_ids),
        )
    )

    return SubmissionValidationResult(
        parsed=parsed,
        errors=tuple(errors),
        ground_truth_version_id=requirements.ground_truth_version_id,
    )


def validate_submission_filename(filename: str) -> tuple[SubmissionValidationError, ...]:
    if Path(filename).suffix.lower() != ALLOWED_SUBMISSION_SUFFIX:
        return (
            SubmissionValidationError(
                field_name="file",
                error_code="invalid_file_extension",
                message="Submission file must be a .txt file.",
            ),
        )
    return ()


def validate_submission_size(
    size_bytes: int,
    *,
    max_upload_bytes: int,
) -> tuple[SubmissionValidationError, ...]:
    if size_bytes > max_upload_bytes:
        return (
            SubmissionValidationError(
                field_name="file",
                error_code="file_too_large",
                message=f"Submission file is larger than {max_upload_bytes} bytes.",
            ),
        )
    return ()


def store_submission_file(
    settings: Settings,
    *,
    internal_team_id: int,
    subtask: str,
    filename: str,
    content: bytes,
) -> StoredSubmissionFile:
    digest = sha256_bytes(content)
    destination_dir = settings.submissions_dir / f"team-{internal_team_id}" / subtask
    destination_dir.mkdir(parents=True, exist_ok=True)
    timestamp = jst_now_text().replace(" ", "_").replace(":", "")
    destination = destination_dir / f"{timestamp}_{safe_filename(filename)}"
    destination.write_bytes(content)
    return StoredSubmissionFile(path=destination, sha256=digest, size_bytes=len(content))


def parse_jst_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=JST)


def is_submission_period_open(period: SubmissionPeriod, *, now_jst: datetime) -> bool:
    if period.is_open_override:
        return True
    if period.starts_at_jst is not None and now_jst < parse_jst_datetime(period.starts_at_jst):
        return False
    return now_jst <= parse_jst_datetime(period.deadline_at_jst)


def get_open_submission_period(
    connection: sqlite3.Connection,
    *,
    now_jst: datetime | None = None,
) -> SubmissionPeriod | None:
    current_jst = now_jst or datetime.now(JST)
    periods = list_submission_periods(connection)
    for period in periods:
        if is_submission_period_open(period, now_jst=current_jst):
            return period
    return None


def get_submission_period_by_name(
    connection: sqlite3.Connection,
    period_name: str,
) -> SubmissionPeriod | None:
    row = connection.execute(
        """
        SELECT id, name, starts_at_jst, deadline_at_jst, is_open_override
        FROM submission_periods
        WHERE name = ?
        """,
        (period_name,),
    ).fetchone()
    if row is None:
        return None
    return SubmissionPeriod(
        id=row["id"],
        name=row["name"],
        starts_at_jst=row["starts_at_jst"],
        deadline_at_jst=row["deadline_at_jst"],
        is_open_override=bool(row["is_open_override"]),
    )


def list_submission_periods(connection: sqlite3.Connection) -> tuple[SubmissionPeriod, ...]:
    rows = connection.execute(
        """
        SELECT id, name, starts_at_jst, deadline_at_jst, is_open_override
        FROM submission_periods
        ORDER BY
          CASE name
            WHEN 'normal' THEN 1
            WHEN 'late' THEN 2
            ELSE 3
          END,
          id
        """
    ).fetchall()
    return tuple(
        SubmissionPeriod(
            id=row["id"],
            name=row["name"],
            starts_at_jst=row["starts_at_jst"],
            deadline_at_jst=row["deadline_at_jst"],
            is_open_override=bool(row["is_open_override"]),
        )
        for row in rows
    )


def get_normal_submission_period(connection: sqlite3.Connection) -> SubmissionPeriod:
    row = connection.execute(
        """
        SELECT id, name, starts_at_jst, deadline_at_jst, is_open_override
        FROM submission_periods
        WHERE name = 'normal'
        """
    ).fetchone()
    if row is None:
        raise RuntimeError("Normal submission period is not configured.")
    return SubmissionPeriod(
        id=row["id"],
        name=row["name"],
        starts_at_jst=row["starts_at_jst"],
        deadline_at_jst=row["deadline_at_jst"],
        is_open_override=bool(row["is_open_override"]),
    )


def update_submission_period(
    connection: sqlite3.Connection,
    *,
    period_name: str,
    starts_at_jst: str | None,
    deadline_at_jst: str,
    is_open_override: bool,
) -> bool:
    cursor = connection.execute(
        """
        UPDATE submission_periods
        SET starts_at_jst = ?,
            deadline_at_jst = ?,
            is_open_override = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE name = ?
        """,
        (
            starts_at_jst,
            deadline_at_jst,
            int(is_open_override),
            period_name,
        ),
    )
    connection.commit()
    return cursor.rowcount > 0


def create_submission_attempt(
    connection: sqlite3.Connection,
    *,
    internal_team_id: int,
    subtask: str,
    submission_period_id: int,
    status: str,
    original_filename: str,
    file_size_bytes: int,
    stored_file_path: Path | None,
    file_sha256: str | None,
    validation_summary: str | None,
    ground_truth_version_id: int | None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO submissions (
          team_id,
          subtask,
          submission_period_id,
          status,
          original_filename,
          stored_file_path,
          file_sha256,
          file_size_bytes,
          submitted_at_jst,
          validation_summary,
          ground_truth_version_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            internal_team_id,
            subtask,
            submission_period_id,
            status,
            original_filename,
            str(stored_file_path) if stored_file_path is not None else None,
            file_sha256,
            file_size_bytes,
            jst_now_text(),
            validation_summary,
            ground_truth_version_id,
        ),
    )
    connection.commit()
    return cursor.lastrowid


def has_successful_submission(
    connection: sqlite3.Connection,
    *,
    internal_team_id: int,
    subtask: str,
    submission_period_id: int,
) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM submissions
        WHERE team_id = ?
          AND subtask = ?
          AND submission_period_id = ?
          AND status IN ('accepted', 'evaluated', 'evaluation_failed')
        LIMIT 1
        """,
        (internal_team_id, subtask, submission_period_id),
    ).fetchone()
    return row is not None


def persist_validation_errors(
    connection: sqlite3.Connection,
    *,
    submission_id: int,
    errors: tuple[SubmissionValidationError, ...],
) -> None:
    connection.executemany(
        """
        INSERT INTO validation_errors (
          submission_id,
          line_number,
          field_name,
          error_code,
          message,
          severity
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                submission_id,
                error.line_number,
                error.field_name,
                error.error_code,
                error.message,
                error.severity,
            )
            for error in errors
        ],
    )
    connection.commit()


def persist_submission_runs(
    connection: sqlite3.Connection,
    *,
    submission_id: int,
    parsed: ParsedSubmission,
) -> None:
    rows = []
    for run_id in parsed.run_ids:
        run_lines = [line for line in parsed.lines if line.run_id == run_id]
        query_count = len({line.topic_id for line in run_lines})
        rows.append((submission_id, run_id, len(run_lines), query_count))

    connection.executemany(
        """
        INSERT INTO runs (submission_id, run_id, line_count, query_count)
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )
    connection.commit()
