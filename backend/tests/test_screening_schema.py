"""Schema tests for ScreeningReport (Prompt 3, section A)."""

import pytest
from pydantic import ValidationError

from app.schemas.screening import ScreeningReport


def _report(**overrides):
    base = dict(
        candidate_id="cand_001",
        candidate_name="Ada Lovelace",
        strengths=["Python expertise"],
        gaps=["Containerization not specified"],
        evidence=["Skills list includes Python"],
        interview_questions=["Describe a production API you shipped."],
    )
    base.update(overrides)
    return ScreeningReport(**base)


def test_valid_report_has_required_fields():
    r = _report()
    assert r.candidate_id == "cand_001"
    assert r.candidate_name == "Ada Lovelace"
    assert isinstance(r.strengths, list)
    assert isinstance(r.gaps, list)
    assert isinstance(r.evidence, list)
    assert isinstance(r.interview_questions, list)


def test_valid_minimal_report_defaults_optionals_to_none():
    r = _report()
    assert r.overall_assessment is None


def test_overall_assessment_is_optional_and_can_be_set():
    r = _report(overall_assessment="Evidence indicates strong backend depth.")
    assert r.overall_assessment == (
        "Evidence indicates strong backend depth."
    )


@pytest.mark.parametrize("field", ["candidate_id", "candidate_name"])
def test_missing_required_field_rejected(field):
    data = {
        "candidate_id": "c1",
        "candidate_name": "Ann",
        "strengths": ["a"],
        "gaps": ["b"],
        "evidence": ["c"],
        "interview_questions": ["q"],
    }
    del data[field]
    with pytest.raises(ValidationError):
        ScreeningReport(**data)


@pytest.mark.parametrize(
    "field, bad_value",
    [
        ("strengths", "not-a-list"),
        ("gaps", 42),
        ("evidence", {"x": 1}),
        ("interview_questions", "single string"),
    ],
)
def test_malformed_list_fields_rejected(field, bad_value):
    data = {
        "candidate_id": "c1",
        "candidate_name": "Ann",
        "strengths": ["a"],
        "gaps": ["b"],
        "evidence": ["c"],
        "interview_questions": ["q"],
    }
    data[field] = bad_value
    with pytest.raises(ValidationError):
        ScreeningReport(**data)


def test_malformed_non_string_item_rejected():
    with pytest.raises(ValidationError):
        _report(strengths=["ok", 123])


def test_malformed_json_parsing_rejects():
    with pytest.raises(ValidationError):
        ScreeningReport.model_validate_json("{not valid json")


def test_model_validate_json_accepts_valid_reports():
    r = ScreeningReport.model_validate_json(
        '{"candidate_id": "c1", "candidate_name": "Ann", '
        '"strengths": ["a"], "gaps": ["b"], "evidence": ["c"], '
        '"interview_questions": ["q"]}'
    )
    assert r.candidate_id == "c1"