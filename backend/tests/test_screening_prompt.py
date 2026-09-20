"""Prompt tests (Prompt 3, section B)."""

from app.services.prompts import SYSTEM_INSTRUCTION, build_screening_prompt
from app.services.screening_input import build_screening_input

JOB_DESCRIPTION = (
    "Backend Engineer - Build production REST APIs with Python and FastAPI, "
    "own PostgreSQL schema design, require 2+ years of experience, comfortable "
    "with Docker and working in a startup."
)


def _candidate_text(candidate_factory):
    candidate = candidate_factory(id="cand_007", name="Grace Hopper")
    return build_screening_input(candidate).to_prompt_text()


def test_system_instruction_covers_ground_rules():
    assert "recruiting assistant" in SYSTEM_INSTRUCTION
    assert "do not make hiring decisions" in SYSTEM_INSTRUCTION.lower()
    assert "Never invent facts" in SYSTEM_INSTRUCTION
    assert "not specified" in SYSTEM_INSTRUCTION
    assert "hiring recommendation" in SYSTEM_INSTRUCTION


def test_prompt_includes_job_description(candidate_factory):
    text = _candidate_text(candidate_factory)
    prompt = build_screening_prompt(JOB_DESCRIPTION, text)
    assert "JOB DESCRIPTION:" in prompt
    for token in ("Python", "FastAPI", "PostgreSQL", "Docker", "2+ years"):
        assert token in prompt


def test_prompt_includes_candidate_information(candidate_factory):
    text = _candidate_text(candidate_factory)
    prompt = build_screening_prompt(JOB_DESCRIPTION, text)
    assert "CANDIDATE:" in prompt
    assert "cand_007" in prompt
    assert "Grace Hopper" in prompt
    assert "Backend Engineer" in prompt
    assert "Python, SQL, FastAPI" in prompt


def test_prompt_repeats_anti_hallucination_rules(candidate_factory):
    prompt = build_screening_prompt(
        JOB_DESCRIPTION, _candidate_text(candidate_factory)
    )
    assert "Never invent facts" in prompt
    assert "not specified" in prompt
    assert "hiring decision" in prompt
    assert "evidence" in prompt.lower()


def test_forbidden_fields_are_not_sent_to_llm(candidate_factory):
    candidate = candidate_factory(
        id="cand_007",
        name="Grace Hopper",
        is_shortlisted=True,
        applied_date=None,
    )
    text = build_screening_input(candidate).to_prompt_text()
    for forbidden in (
        "is_shortlisted",
        "applied_date",
        "embedding",
        "vec0",
        "vector",
        "distance",
    ):
        assert forbidden not in text.lower()


def test_candidate_text_is_deterministic(candidate_factory):
    candidate = candidate_factory(id="cand_007", name="Grace Hopper")
    t1 = build_screening_input(candidate).to_prompt_text()
    t2 = build_screening_input(candidate).to_prompt_text()
    assert t1 == t2