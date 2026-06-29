from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import log2

from app.submissions import ParsedSubmission, SubmissionLine


@dataclass(frozen=True)
class RunMetric:
    run_id: str
    metric_name: str
    metric_value: float


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
