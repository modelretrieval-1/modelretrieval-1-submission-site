from __future__ import annotations

import sqlite3
from collections import defaultdict
from csv import DictReader
from dataclasses import dataclass
from math import log2
from pathlib import Path

from app.accounts import Subtask
from app.ground_truth import GroundTruthVersion, jst_now_text
from app.submissions import ParsedSubmission, SubmissionLine


@dataclass(frozen=True)
class RunMetric:
    run_id: str
    metric_name: str
    metric_value: float


@dataclass(frozen=True)
class QueryMetric:
    run_id: str
    topic_id: str
    metric_name: str
    metric_value: float


@dataclass(frozen=True)
class EvaluationResult:
    run_id: str
    metric_name: str
    metric_value: float


@dataclass(frozen=True)
class QueryEvaluationResult:
    run_id: str
    topic_id: str
    metric_name: str
    metric_value: float


@dataclass(frozen=True)
class TeamSubmissionSummary:
    submission_id: int
    subtask: str
    status: str
    original_filename: str
    submitted_at_jst: str
    metrics: tuple[EvaluationResult, ...]


@dataclass(frozen=True)
class LeaderboardRow:
    submission_id: int
    team_public_id: str
    team_display_name: str
    subtask: str
    period_name: str
    run_id: str
    submitted_at_jst: str
    metric_values: dict[str, float]


def dcg(relevance_scores: list[float]) -> float:
    return sum(
        ((2**relevance_score) - 1) / log2(index + 2)
        for index, relevance_score in enumerate(relevance_scores)
    )


def ndcg_at(
    ranked_doc_ids: list[str],
    relevance_by_doc_id: dict[str, float],
    *,
    cutoff: int,
) -> float:
    ranked_relevance = [
        relevance_by_doc_id.get(doc_id, 0.0)
        for doc_id in ranked_doc_ids[:cutoff]
    ]
    ideal_relevance = sorted(relevance_by_doc_id.values(), reverse=True)[:cutoff]
    ideal_dcg = dcg(ideal_relevance)
    if ideal_dcg == 0:
        return 0.0
    return dcg(ranked_relevance) / ideal_dcg


def mean_reciprocal_rank(ranked_doc_ids: list[str], relevant_doc_id: str) -> float:
    for index, doc_id in enumerate(ranked_doc_ids, start=1):
        if doc_id == relevant_doc_id:
            return 1 / index
    return 0.0


def evaluate_subtask_a(
    parsed: ParsedSubmission,
    relevance_by_topic_doc: dict[tuple[str, str], float],
    *,
    cutoffs: tuple[int, ...] = (1, 3, 5),
) -> tuple[RunMetric, ...]:
    metrics: list[RunMetric] = []
    lines_by_run_topic = _lines_by_run_topic(parsed.lines)
    topics = sorted({topic_id for topic_id, _doc_id in relevance_by_topic_doc})

    for run_id in parsed.run_ids:
        for cutoff in cutoffs:
            query_scores = []
            for topic_id in topics:
                run_lines = lines_by_run_topic[(run_id, topic_id)]
                ranked_doc_ids = _ranked_doc_ids(run_lines)
                relevance_by_doc_id = {
                    doc_id: relevance
                    for (relevance_topic_id, doc_id), relevance in relevance_by_topic_doc.items()
                    if relevance_topic_id == topic_id
                }
                query_scores.append(
                    ndcg_at(
                        ranked_doc_ids,
                        relevance_by_doc_id,
                        cutoff=cutoff,
                    )
                )
            metric_value = sum(query_scores) / len(query_scores) if query_scores else 0.0
            metrics.append(
                RunMetric(
                    run_id=run_id,
                    metric_name=f"ndcg@{cutoff}",
                    metric_value=metric_value,
                )
            )

    return tuple(metrics)


def evaluate_subtask_a_query_metrics(
    parsed: ParsedSubmission,
    relevance_by_topic_doc: dict[tuple[str, str], float],
    *,
    cutoffs: tuple[int, ...] = (1, 3, 5),
) -> tuple[QueryMetric, ...]:
    metrics: list[QueryMetric] = []
    lines_by_run_topic = _lines_by_run_topic(parsed.lines)
    topics = sorted({topic_id for topic_id, _doc_id in relevance_by_topic_doc})

    for run_id in parsed.run_ids:
        for topic_id in topics:
            run_lines = lines_by_run_topic[(run_id, topic_id)]
            ranked_doc_ids = _ranked_doc_ids(run_lines)
            relevance_by_doc_id = {
                doc_id: relevance
                for (relevance_topic_id, doc_id), relevance in relevance_by_topic_doc.items()
                if relevance_topic_id == topic_id
            }
            for cutoff in cutoffs:
                metrics.append(
                    QueryMetric(
                        run_id=run_id,
                        topic_id=topic_id,
                        metric_name=f"ndcg@{cutoff}",
                        metric_value=ndcg_at(
                            ranked_doc_ids,
                            relevance_by_doc_id,
                            cutoff=cutoff,
                        ),
                    )
                )

    return tuple(metrics)


def evaluate_subtask_b(
    parsed: ParsedSubmission,
    relevant_doc_by_topic: dict[str, str],
) -> tuple[RunMetric, ...]:
    metrics: list[RunMetric] = []
    lines_by_run_topic = _lines_by_run_topic(parsed.lines)

    for run_id in parsed.run_ids:
        query_scores = []
        for topic_id, relevant_doc_id in sorted(relevant_doc_by_topic.items()):
            run_lines = lines_by_run_topic[(run_id, topic_id)]
            query_scores.append(
                mean_reciprocal_rank(
                    _ranked_doc_ids(run_lines),
                    relevant_doc_id,
                )
            )
        metric_value = sum(query_scores) / len(query_scores) if query_scores else 0.0
        metrics.append(
            RunMetric(
                run_id=run_id,
                metric_name="mrr",
                metric_value=metric_value,
            )
        )

    return tuple(metrics)


def evaluate_subtask_b_query_metrics(
    parsed: ParsedSubmission,
    relevant_doc_by_topic: dict[str, str],
) -> tuple[QueryMetric, ...]:
    metrics: list[QueryMetric] = []
    lines_by_run_topic = _lines_by_run_topic(parsed.lines)

    for run_id in parsed.run_ids:
        for topic_id, relevant_doc_id in sorted(relevant_doc_by_topic.items()):
            run_lines = lines_by_run_topic[(run_id, topic_id)]
            metrics.append(
                QueryMetric(
                    run_id=run_id,
                    topic_id=topic_id,
                    metric_name="reciprocal_rank",
                    metric_value=mean_reciprocal_rank(
                        _ranked_doc_ids(run_lines),
                        relevant_doc_id,
                    ),
                )
            )

    return tuple(metrics)


def load_subtask_a_relevance(
    ground_truth_version: GroundTruthVersion,
) -> dict[tuple[str, str], float]:
    rows = DictReader(
        Path(ground_truth_version.stored_file_path).read_text(encoding="utf-8-sig").splitlines()
    )
    relevance: dict[tuple[str, str], float] = {}
    for row in rows:
        topic_id = (row.get("task_id") or "").strip()
        doc_id = (row.get("model_id") or "").strip()
        relevance_score = (row.get("relevance_score") or "").strip()
        if topic_id and doc_id and relevance_score:
            relevance[(topic_id, doc_id)] = float(relevance_score)
    return relevance


def load_subtask_b_relevant_docs(
    ground_truth_version: GroundTruthVersion,
) -> dict[str, str]:
    rows = DictReader(
        Path(ground_truth_version.stored_file_path).read_text(encoding="utf-8-sig").splitlines()
    )
    relevant_docs: dict[str, str] = {}
    for row in rows:
        topic_id = (row.get("image_id") or "").strip()
        doc_id = (row.get("model_id") or "").strip()
        if topic_id and doc_id:
            relevant_docs[topic_id] = doc_id
    return relevant_docs


def evaluate_submission(
    parsed: ParsedSubmission,
    *,
    subtask: Subtask,
    ground_truth_version: GroundTruthVersion,
) -> tuple[RunMetric, ...]:
    if subtask == "A":
        return evaluate_subtask_a(
            parsed,
            load_subtask_a_relevance(ground_truth_version),
        )
    return evaluate_subtask_b(
        parsed,
        load_subtask_b_relevant_docs(ground_truth_version),
    )


def evaluate_submission_query_metrics(
    parsed: ParsedSubmission,
    *,
    subtask: Subtask,
    ground_truth_version: GroundTruthVersion,
) -> tuple[QueryMetric, ...]:
    if subtask == "A":
        return evaluate_subtask_a_query_metrics(
            parsed,
            load_subtask_a_relevance(ground_truth_version),
        )
    return evaluate_subtask_b_query_metrics(
        parsed,
        load_subtask_b_relevant_docs(ground_truth_version),
    )


def persist_evaluation_results(
    connection: sqlite3.Connection,
    *,
    submission_id: int,
    ground_truth_version_id: int,
    metrics: tuple[RunMetric, ...],
    query_metrics: tuple[QueryMetric, ...] = (),
) -> None:
    run_rows = connection.execute(
        """
        SELECT id, run_id
        FROM runs
        WHERE submission_id = ?
        """,
        (submission_id,),
    ).fetchall()
    run_database_ids = {row["run_id"]: row["id"] for row in run_rows}
    missing_run_ids = sorted(
        (
            {metric.run_id for metric in metrics}
            | {metric.run_id for metric in query_metrics}
        )
        - set(run_database_ids)
    )
    if missing_run_ids:
        raise ValueError(f"Missing run rows for RunID(s): {', '.join(missing_run_ids)}")

    connection.executemany(
        """
        INSERT INTO evaluation_results (
          submission_id,
          run_id,
          ground_truth_version_id,
          metric_name,
          metric_value,
          created_at_jst
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                submission_id,
                run_database_ids[metric.run_id],
                ground_truth_version_id,
                metric.metric_name,
                metric.metric_value,
                jst_now_text(),
            )
            for metric in metrics
        ],
    )
    connection.executemany(
        """
        INSERT INTO evaluation_query_results (
          submission_id,
          run_id,
          ground_truth_version_id,
          topic_id,
          metric_name,
          metric_value,
          created_at_jst
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                submission_id,
                run_database_ids[metric.run_id],
                ground_truth_version_id,
                metric.topic_id,
                metric.metric_name,
                metric.metric_value,
                jst_now_text(),
            )
            for metric in query_metrics
        ],
    )
    connection.execute(
        """
        UPDATE submissions
        SET status = 'evaluated'
        WHERE id = ?
        """,
        (submission_id,),
    )
    connection.commit()


def mark_evaluation_failed(connection: sqlite3.Connection, *, submission_id: int) -> None:
    connection.execute(
        """
        UPDATE submissions
        SET status = 'evaluation_failed'
        WHERE id = ?
        """,
        (submission_id,),
    )
    connection.commit()


def list_submission_results(
    connection: sqlite3.Connection,
    *,
    submission_id: int,
) -> tuple[EvaluationResult, ...]:
    rows = connection.execute(
        """
        SELECT
          runs.run_id,
          evaluation_results.metric_name,
          evaluation_results.metric_value
        FROM evaluation_results
        JOIN runs ON runs.id = evaluation_results.run_id
        WHERE evaluation_results.submission_id = ?
        ORDER BY runs.run_id, evaluation_results.metric_name
        """,
        (submission_id,),
    ).fetchall()
    return tuple(
        EvaluationResult(
            run_id=row["run_id"],
            metric_name=row["metric_name"],
            metric_value=row["metric_value"],
        )
        for row in rows
    )


def list_submission_query_results(
    connection: sqlite3.Connection,
    *,
    submission_id: int,
) -> tuple[QueryEvaluationResult, ...]:
    rows = connection.execute(
        """
        SELECT
          runs.run_id,
          evaluation_query_results.topic_id,
          evaluation_query_results.metric_name,
          evaluation_query_results.metric_value
        FROM evaluation_query_results
        JOIN runs ON runs.id = evaluation_query_results.run_id
        WHERE evaluation_query_results.submission_id = ?
        ORDER BY
          runs.run_id,
          evaluation_query_results.topic_id,
          evaluation_query_results.metric_name
        """,
        (submission_id,),
    ).fetchall()
    return tuple(
        QueryEvaluationResult(
            run_id=row["run_id"],
            topic_id=row["topic_id"],
            metric_name=row["metric_name"],
            metric_value=row["metric_value"],
        )
        for row in rows
    )


def list_latest_team_submission_summaries(
    connection: sqlite3.Connection,
    *,
    internal_team_id: int,
) -> tuple[TeamSubmissionSummary, ...]:
    rows = connection.execute(
        """
        SELECT
          id,
          subtask,
          status,
          original_filename,
          submitted_at_jst
        FROM submissions
        WHERE team_id = ?
        ORDER BY subtask, id DESC
        """,
        (internal_team_id,),
    ).fetchall()
    latest_by_subtask = {}
    for row in rows:
        latest_by_subtask.setdefault(row["subtask"], row)

    return tuple(
        TeamSubmissionSummary(
            submission_id=row["id"],
            subtask=row["subtask"],
            status=row["status"],
            original_filename=row["original_filename"],
            submitted_at_jst=row["submitted_at_jst"],
            metrics=list_submission_results(connection, submission_id=row["id"]),
        )
        for row in sorted(latest_by_subtask.values(), key=lambda item: item["subtask"])
    )


def list_leaderboard_rows(
    connection: sqlite3.Connection,
    *,
    subtask: str | None = None,
    period_name: str | None = None,
) -> tuple[LeaderboardRow, ...]:
    where_clauses = ["submissions.status = 'evaluated'"]
    parameters: list[str] = []
    if subtask:
        where_clauses.append("submissions.subtask = ?")
        parameters.append(subtask)
    if period_name:
        where_clauses.append("submission_periods.name = ?")
        parameters.append(period_name)

    rows = connection.execute(
        f"""
        SELECT
          submissions.id AS submission_id,
          teams.team_id,
          teams.display_name,
          submissions.subtask,
          submission_periods.name AS period_name,
          runs.run_id,
          submissions.submitted_at_jst,
          evaluation_results.metric_name,
          evaluation_results.metric_value
        FROM evaluation_results
        JOIN runs ON runs.id = evaluation_results.run_id
        JOIN submissions ON submissions.id = evaluation_results.submission_id
        JOIN teams ON teams.id = submissions.team_id
        JOIN submission_periods ON submission_periods.id = submissions.submission_period_id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY submissions.subtask, submission_periods.name, teams.team_id, runs.run_id
        """,
        parameters,
    ).fetchall()

    grouped: dict[tuple[int, str], LeaderboardRow] = {}
    for row in rows:
        key = (row["submission_id"], row["run_id"])
        leaderboard_row = grouped.get(key)
        if leaderboard_row is None:
            leaderboard_row = LeaderboardRow(
                submission_id=row["submission_id"],
                team_public_id=row["team_id"],
                team_display_name=row["display_name"],
                subtask=row["subtask"],
                period_name=row["period_name"],
                run_id=row["run_id"],
                submitted_at_jst=row["submitted_at_jst"],
                metric_values={},
            )
            grouped[key] = leaderboard_row
        leaderboard_row.metric_values[row["metric_name"]] = row["metric_value"]

    return tuple(sorted(grouped.values(), key=_leaderboard_sort_key))


def _leaderboard_sort_key(row: LeaderboardRow) -> tuple[str, str, float, float, str, str]:
    primary_metric = "mrr" if row.subtask == "B" else "ndcg@5"
    secondary_metric = "ndcg@3" if row.subtask == "A" else "mrr"
    return (
        row.subtask,
        row.period_name,
        -row.metric_values.get(primary_metric, 0.0),
        -row.metric_values.get(secondary_metric, 0.0),
        row.team_public_id,
        row.run_id,
    )


def _lines_by_run_topic(
    lines: tuple[SubmissionLine, ...],
) -> defaultdict[tuple[str, str], list[SubmissionLine]]:
    grouped: defaultdict[tuple[str, str], list[SubmissionLine]] = defaultdict(list)
    for line in lines:
        grouped[(line.run_id, line.topic_id)].append(line)
    return grouped


def _ranked_doc_ids(lines: list[SubmissionLine]) -> list[str]:
    return [
        line.doc_id
        for line in sorted(lines, key=lambda line: (line.rank, line.source_order))
    ]
