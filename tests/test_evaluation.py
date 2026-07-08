from pytest import approx

from app.evaluation import (
    dcg,
    evaluate_subtask_a,
    evaluate_subtask_a_query_metrics,
    evaluate_subtask_b,
    evaluate_subtask_b_query_metrics,
    mean_reciprocal_rank,
    ndcg_at,
)
from app.submissions import parse_trec_eval


def test_dcg_uses_exponential_gain_and_log_discount():
    assert dcg([3, 2, 1]) == approx(9.392789260714373)


def test_ndcg_at_returns_one_for_ideal_ranking():
    score = ndcg_at(
        ["m1", "m2", "m3"],
        {"m1": 3, "m2": 2, "m3": 1},
        cutoff=3,
    )

    assert score == approx(1.0)


def test_ndcg_at_discounts_non_ideal_ranking():
    score = ndcg_at(
        ["m2", "m1", "m3"],
        {"m1": 3, "m2": 2, "m3": 1},
        cutoff=3,
    )

    assert score == approx(0.8428282648809379)


def test_ndcg_at_returns_zero_when_query_has_no_relevance():
    score = ndcg_at(
        ["m1", "m2"],
        {"m1": 0, "m2": 0},
        cutoff=3,
    )

    assert score == 0.0


def test_mean_reciprocal_rank_returns_inverse_rank():
    assert mean_reciprocal_rank(["m3", "m2", "m1"], "m1") == approx(1 / 3)


def test_mean_reciprocal_rank_returns_zero_when_relevant_doc_is_absent():
    assert mean_reciprocal_rank(["m3", "m2"], "m1") == 0.0


def test_evaluate_subtask_a_returns_macro_ndcg_per_run_and_cutoff():
    parsed = parse_trec_eval(
        """
        q1 Q0 m1 1 3.0 run-good
        q1 Q0 m2 2 2.0 run-good
        q1 Q0 m3 3 1.0 run-good
        q2 Q0 m2 1 3.0 run-good
        q2 Q0 m1 2 2.0 run-good
        q2 Q0 m3 3 1.0 run-good
        q1 Q0 m2 1 3.0 run-mixed
        q1 Q0 m1 2 2.0 run-mixed
        q1 Q0 m3 3 1.0 run-mixed
        q2 Q0 m3 1 3.0 run-mixed
        q2 Q0 m1 2 2.0 run-mixed
        q2 Q0 m2 3 1.0 run-mixed
        """
    )
    relevance = {
        ("q1", "m1"): 3,
        ("q1", "m2"): 2,
        ("q1", "m3"): 1,
        ("q2", "m1"): 2,
        ("q2", "m2"): 3,
        ("q2", "m3"): 0,
    }

    metrics = evaluate_subtask_a(parsed, relevance, cutoffs=(1, 3))

    by_run_metric = {
        (metric.run_id, metric.metric_name): metric.metric_value
        for metric in metrics
    }
    assert by_run_metric[("run-good", "ndcg@1")] == approx(1.0)
    assert by_run_metric[("run-good", "ndcg@3")] == approx(1.0)
    assert by_run_metric[("run-mixed", "ndcg@1")] == approx((3 / 7) / 2)
    assert by_run_metric[("run-mixed", "ndcg@3")] == approx(0.724625481692726)


def test_evaluate_subtask_a_returns_per_query_ndcg_per_run_and_cutoff():
    parsed = parse_trec_eval(
        """
        q1 Q0 m1 1 3.0 run-good
        q1 Q0 m2 2 2.0 run-good
        q1 Q0 m3 3 1.0 run-good
        q2 Q0 m2 1 3.0 run-good
        q2 Q0 m1 2 2.0 run-good
        q2 Q0 m3 3 1.0 run-good
        q1 Q0 m2 1 3.0 run-mixed
        q1 Q0 m1 2 2.0 run-mixed
        q1 Q0 m3 3 1.0 run-mixed
        q2 Q0 m3 1 3.0 run-mixed
        q2 Q0 m1 2 2.0 run-mixed
        q2 Q0 m2 3 1.0 run-mixed
        """
    )
    relevance = {
        ("q1", "m1"): 3,
        ("q1", "m2"): 2,
        ("q1", "m3"): 1,
        ("q2", "m1"): 2,
        ("q2", "m2"): 3,
        ("q2", "m3"): 0,
    }

    metrics = evaluate_subtask_a_query_metrics(parsed, relevance, cutoffs=(1, 3))

    by_run_query_metric = {
        (metric.run_id, metric.topic_id, metric.metric_name): metric.metric_value
        for metric in metrics
    }
    assert by_run_query_metric[("run-good", "q1", "ndcg@1")] == approx(1.0)
    assert by_run_query_metric[("run-good", "q2", "ndcg@3")] == approx(1.0)
    assert by_run_query_metric[("run-mixed", "q1", "ndcg@1")] == approx(3 / 7)
    assert by_run_query_metric[("run-mixed", "q2", "ndcg@3")] == approx(0.606422698504514)


def test_evaluate_subtask_b_returns_macro_mrr_per_run():
    parsed = parse_trec_eval(
        """
        image1 Q0 model-a 1 3.0 run-a
        image1 Q0 model-b 2 2.0 run-a
        image2 Q0 model-a 1 3.0 run-a
        image2 Q0 model-b 2 2.0 run-a
        image1 Q0 model-b 1 3.0 run-b
        image1 Q0 model-a 2 2.0 run-b
        image2 Q0 model-b 1 3.0 run-b
        image2 Q0 model-a 2 2.0 run-b
        """
    )

    metrics = evaluate_subtask_b(
        parsed,
        {
            "image1": "model-a",
            "image2": "model-b",
        },
    )

    by_run = {metric.run_id: metric.metric_value for metric in metrics}
    assert by_run["run-a"] == approx((1 + 1 / 2) / 2)
    assert by_run["run-b"] == approx((1 / 2 + 1) / 2)


def test_evaluate_subtask_b_matches_image_ids_across_png_suffix():
    # Submission omits .png; ground truth includes it. MRR must still match.
    parsed = parse_trec_eval(
        """
        image1 Q0 model-a 1 3.0 run-a
        image1 Q0 model-b 2 2.0 run-a
        image2 Q0 model-a 1 3.0 run-a
        image2 Q0 model-b 2 2.0 run-a
        """
    )

    metrics = evaluate_subtask_b(
        parsed,
        {
            "image1.png": "model-a",
            "image2.png": "model-b",
        },
    )

    by_run = {metric.run_id: metric.metric_value for metric in metrics}
    assert by_run["run-a"] == approx((1 + 1 / 2) / 2)


def test_evaluate_subtask_b_returns_per_query_reciprocal_rank():
    parsed = parse_trec_eval(
        """
        image1 Q0 model-a 1 3.0 run-a
        image1 Q0 model-b 2 2.0 run-a
        image2 Q0 model-a 1 3.0 run-a
        image2 Q0 model-b 2 2.0 run-a
        """
    )

    metrics = evaluate_subtask_b_query_metrics(
        parsed,
        {
            "image1": "model-a",
            "image2": "model-b",
        },
    )

    by_query = {metric.topic_id: metric.metric_value for metric in metrics}
    assert {metric.metric_name for metric in metrics} == {"reciprocal_rank"}
    assert by_query["image1"] == approx(1.0)
    assert by_query["image2"] == approx(1 / 2)
