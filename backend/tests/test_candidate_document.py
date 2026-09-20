from app.services.candidate_document import build_candidate_document


def test_document_contains_semantic_fields(candidate_factory):
    candidate = candidate_factory(
        id="cand_042",
        name="Grace Hopper",
        target_role="ML Engineer",
        years_experience=9,
        source="Referral",
        skills=["Python", "PyTorch", "Kubernetes"],
        notes="Led model serving at scale.",
        applied_date=None,
        is_shortlisted=True,
    )
    doc = build_candidate_document(candidate)

    assert "Name: Grace Hopper" in doc
    assert "Target Role: ML Engineer" in doc
    assert "Years of Experience: 9" in doc
    assert "Skills: Python, PyTorch, Kubernetes" in doc
    assert "Notes: Led model serving at scale." in doc


def test_document_excludes_recruiter_state(candidate_factory):
    candidate = candidate_factory(
        source="Agency XYZ",
        applied_date=None,
        is_shortlisted=True,
    )
    doc = build_candidate_document(candidate)

    assert "is_shortlisted" not in doc
    assert "Shortlisted" not in doc
    assert "applied_date" not in doc
    assert "Agency XYZ" not in doc
    assert "Recommended" not in doc


def test_document_is_deterministic(candidate_factory):
    candidate = candidate_factory()
    assert build_candidate_document(candidate) == build_candidate_document(candidate)


def test_document_handles_empty_skills(candidate_factory):
    candidate = candidate_factory(skills=[])
    doc = build_candidate_document(candidate)
    assert "Skills: " in doc
    assert "Skills: \n" in doc or doc.endswith("Skills: ")