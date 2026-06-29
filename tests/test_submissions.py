from app.ground_truth import GroundTruthRequirements
from app.submissions import (
    parse_trec_eval,
    validate_query_model_completeness,
    validate_submission_against_requirements,
)


def test_valid_trec_eval_lines_parse_successfully():
    parsed = parse_trec_eval(
        """
        1 Q0 1 1 0.99 Run01
        1 Q0 7 2 0.95 Run01
        2 Q0 1 1 -2.5 Run02
        """
    )

    assert parsed.is_valid
    assert parsed.run_ids == ("Run01", "Run02")
    assert len(parsed.lines) == 3
    assert parsed.lines[0].topic_id == "1"
    assert parsed.lines[0].doc_id == "1"
    assert parsed.lines[0].rank == 1
    assert parsed.lines[0].score == 0.99
    assert parsed.lines[0].run_id == "Run01"


def test_wrong_field_count_is_rejected_with_line_number():
    parsed = parse_trec_eval("1 Q0 1 1 0.99\n")

    assert not parsed.is_valid
    assert parsed.errors[0].line_number == 1
    assert parsed.errors[0].error_code == "field_count"
    assert parsed.errors[0].message == "Expected 6 fields, found 5."


def test_non_q0_token_is_rejected():
    parsed = parse_trec_eval("1 Q1 1 1 0.99 Run01\n")

    assert not parsed.is_valid
    assert parsed.errors[0].line_number == 1
    assert parsed.errors[0].field_name == "Q0"
    assert parsed.errors[0].error_code == "invalid_q0"


def test_non_integer_rank_is_rejected():
    parsed = parse_trec_eval("1 Q0 1 first 0.99 Run01\n")

    assert not parsed.is_valid
    assert parsed.errors[0].field_name == "Rank"
    assert parsed.errors[0].error_code == "invalid_rank"
    assert not parsed.lines


def test_non_positive_rank_is_rejected():
    parsed = parse_trec_eval("1 Q0 1 0 0.99 Run01\n")

    assert not parsed.is_valid
    assert parsed.errors[0].field_name == "Rank"
    assert parsed.errors[0].error_code == "invalid_rank"


def test_non_numeric_score_is_rejected():
    parsed = parse_trec_eval("1 Q0 1 1 high Run01\n")

    assert not parsed.is_valid
    assert parsed.errors[0].field_name == "Score"
    assert parsed.errors[0].error_code == "invalid_score"
    assert not parsed.lines


def test_more_than_five_distinct_runs_is_rejected():
    content = "\n".join(
        f"1 Q0 1 1 0.{index} Run0{index}"
        for index in range(1, 7)
    )

    parsed = parse_trec_eval(content)

    assert not parsed.is_valid
    assert parsed.errors[0].error_code == "too_many_runs"
    assert parsed.errors[0].message == "Submission contains 6 run IDs; maximum is 5."


def test_blank_lines_are_ignored():
    parsed = parse_trec_eval("\n\n1 Q0 1 1 0.99 Run01\n\n")

    assert parsed.is_valid
    assert len(parsed.lines) == 1
    assert parsed.lines[0].line_number == 3


def test_duplicate_run_topic_doc_is_rejected():
    parsed = parse_trec_eval(
        """
        1 Q0 1 1 0.99 Run01
        1 Q0 1 2 0.95 Run01
        """
    )

    assert not parsed.is_valid
    assert parsed.errors[0].error_code == "duplicate_run_topic_doc"
    assert parsed.errors[0].line_number == 3
    assert "line 2" in parsed.errors[0].message


def test_duplicate_ranks_are_allowed_when_score_order_matches_line_order():
    parsed = parse_trec_eval(
        """
        1 Q0 A 1 0.90 Run01
        1 Q0 B 1 0.80 Run01
        """
    )

    assert parsed.is_valid


def test_tied_scores_are_allowed_and_use_line_order():
    parsed = parse_trec_eval(
        """
        1 Q0 A 1 0.90 Run01
        1 Q0 B 2 0.90 Run01
        """
    )

    assert parsed.is_valid


def test_higher_score_below_lower_score_is_rejected():
    parsed = parse_trec_eval(
        """
        1 Q0 A 1 0.80 Run01
        1 Q0 B 2 0.90 Run01
        """
    )

    assert not parsed.is_valid
    assert parsed.errors[0].error_code == "rank_score_order_mismatch"
    assert parsed.errors[0].line_number == 2
    assert parsed.errors[0].severity == "warning"


def test_rank_values_that_disagree_with_score_order_are_rejected():
    parsed = parse_trec_eval(
        """
        1 Q0 A 2 0.90 Run01
        1 Q0 B 1 0.80 Run01
        """
    )

    assert not parsed.is_valid
    assert parsed.errors[0].error_code == "rank_score_order_mismatch"


def test_query_model_completeness_accepts_complete_run():
    parsed = parse_trec_eval(
        """
        Q1 Q0 M1 1 0.9 Run01
        Q1 Q0 M2 2 0.8 Run01
        Q2 Q0 M1 1 0.7 Run01
        Q2 Q0 M2 2 0.6 Run01
        """
    )

    errors = validate_query_model_completeness(
        parsed,
        required_topic_ids={"Q1", "Q2"},
        required_doc_ids={"M1", "M2"},
    )

    assert errors == ()


def test_query_model_completeness_rejects_missing_topic():
    parsed = parse_trec_eval(
        """
        Q1 Q0 M1 1 0.9 Run01
        Q1 Q0 M2 2 0.8 Run01
        """
    )

    errors = validate_query_model_completeness(
        parsed,
        required_topic_ids={"Q1", "Q2"},
        required_doc_ids={"M1", "M2"},
    )

    assert errors[0].error_code == "missing_topic_id"
    assert errors[0].message == "RunID Run01 is missing topicID Q2."


def test_query_model_completeness_rejects_missing_model_for_query():
    parsed = parse_trec_eval(
        """
        Q1 Q0 M1 1 0.9 Run01
        Q2 Q0 M1 1 0.7 Run01
        Q2 Q0 M2 2 0.6 Run01
        """
    )

    errors = validate_query_model_completeness(
        parsed,
        required_topic_ids={"Q1", "Q2"},
        required_doc_ids={"M1", "M2"},
    )

    assert errors[0].error_code == "missing_doc_id"
    assert errors[0].message == "RunID Run01 topicID Q1 is missing docID M2."


def test_query_model_completeness_rejects_unknown_topic_id():
    parsed = parse_trec_eval("Q3 Q0 M1 1 0.9 Run01\n")

    errors = validate_query_model_completeness(
        parsed,
        required_topic_ids={"Q1"},
        required_doc_ids={"M1"},
    )

    assert errors[0].line_number == 1
    assert errors[0].field_name == "topicID"
    assert errors[0].error_code == "unknown_topic_id"


def test_query_model_completeness_rejects_unknown_doc_id():
    parsed = parse_trec_eval("Q1 Q0 M3 1 0.9 Run01\n")

    errors = validate_query_model_completeness(
        parsed,
        required_topic_ids={"Q1"},
        required_doc_ids={"M1"},
    )

    assert errors[0].line_number == 1
    assert errors[0].field_name == "docID"
    assert errors[0].error_code == "unknown_doc_id"


def test_query_model_completeness_checks_each_run_independently():
    parsed = parse_trec_eval(
        """
        Q1 Q0 M1 1 0.9 Run01
        Q1 Q0 M2 2 0.8 Run01
        Q1 Q0 M1 1 0.9 Run02
        """
    )

    errors = validate_query_model_completeness(
        parsed,
        required_topic_ids={"Q1"},
        required_doc_ids={"M1", "M2"},
    )

    assert len(errors) == 1
    assert errors[0].message == "RunID Run02 topicID Q1 is missing docID M2."


def test_validate_submission_against_requirements_accepts_complete_submission():
    requirements = GroundTruthRequirements(
        subtask="A",
        ground_truth_version_id=42,
        required_topic_ids=frozenset({"Q1"}),
        required_doc_ids=frozenset({"M1", "M2"}),
    )

    result = validate_submission_against_requirements(
        """
        Q1 Q0 M1 1 0.9 Run01
        Q1 Q0 M2 2 0.8 Run01
        """,
        requirements,
    )

    assert result.is_valid
    assert result.ground_truth_version_id == 42


def test_validate_submission_against_requirements_reports_missing_active_ground_truth():
    result = validate_submission_against_requirements("Q1 Q0 M1 1 0.9 Run01", None)

    assert not result.is_valid
    assert result.errors[0].error_code == "missing_active_ground_truth"


def test_validate_submission_against_requirements_reports_completeness_errors():
    requirements = GroundTruthRequirements(
        subtask="A",
        ground_truth_version_id=42,
        required_topic_ids=frozenset({"Q1"}),
        required_doc_ids=frozenset({"M1", "M2"}),
    )

    result = validate_submission_against_requirements("Q1 Q0 M1 1 0.9 Run01", requirements)

    assert not result.is_valid
    assert result.ground_truth_version_id == 42
    assert result.errors[0].error_code == "missing_doc_id"
