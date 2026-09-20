"""REST API tests: health, candidate listing, detail, shortlisting, OpenAPI.

Uses the `api_client` fixture (get_db overridden to a fresh temp DB with 5
controlled candidates). No Gemini calls anywhere.
"""

import pytest

from app.main import app

CANDIDATE_FIELDS = {
    "id",
    "name",
    "target_role",
    "years_experience",
    "source",
    "skills",
    "notes",
    "applied_date",
    "is_shortlisted",
}


def _ids(items):
    return [i["id"] for i in items]


# ---------------------------------------------------------------- health ----
def test_health(api_client):
    assert api_client.get("/health").status_code == 200
    assert api_client.get("/health").json() == {"status": "ok"}


# ------------------------------------------------------------ listing -------
def test_list_candidates_default_page(api_client):
    body = api_client.get("/candidates").json()
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total_pages"] == 1
    assert len(body["items"]) == 5


def test_list_candidate_has_clean_contract(api_client):
    item = api_client.get("/candidates").json()["items"][0]
    assert set(item.keys()) == CANDIDATE_FIELDS
    assert "embedding" not in item
    assert "distance" not in item


def test_pagination_slices_and_metadata(api_client):
    p1 = api_client.get("/candidates", params={"page": 1, "page_size": 2}).json()
    assert (p1["total"], p1["total_pages"]) == (5, 3)
    assert len(p1["items"]) == 2
    assert p1["items"][0]["id"] == "cand_a"  # default name sort

    p3 = api_client.get("/candidates", params={"page": 3, "page_size": 2}).json()
    assert _ids(p3["items"]) == ["cand_e"]
    assert p3["total_pages"] == 3

    p4 = api_client.get("/candidates", params={"page": 4, "page_size": 2}).json()
    assert p4["items"] == []
    assert p4["total"] == 5  # total reflects all matching rows, page beyond end


def test_search_across_name_role_skills_notes(api_client):
    by_skill = api_client.get("/candidates", params={"search": "python"}).json()
    assert set(_ids(by_skill["items"])) == {"cand_a", "cand_c", "cand_d", "cand_e"}

    by_role = api_client.get("/candidates", params={"search": "backend"}).json()
    assert set(_ids(by_role["items"])) == {"cand_a", "cand_c", "cand_e"}

    by_note = api_client.get("/candidates", params={"search": "startup"}).json()
    assert _ids(by_note["items"]) == ["cand_a"]

    upper = api_client.get("/candidates", params={"search": "PYTHON"}).json()
    assert _ids(upper["items"]) == _ids(by_skill["items"])


def test_target_role_filter_exact_case_insensitive_normalized(api_client):
    r = api_client.get(
        "/candidates", params={"target_role": "Backend   Engineer"}
    ).json()
    assert set(_ids(r["items"])) == {"cand_a", "cand_c", "cand_e"}

    lower = api_client.get("/candidates", params={"target_role": "backend engineer"}).json()
    assert _ids(lower["items"]) == _ids(r["items"])


def test_experience_range_filter(api_client):
    r = api_client.get(
        "/candidates", params={"min_experience": 3, "max_experience": 5}
    ).json()
    assert set(_ids(r["items"])) == {"cand_a", "cand_d"}  # 5yrs and 3yrs


def test_source_filter_case_insensitive(api_client):
    r = api_client.get("/candidates", params={"source": "naukri"}).json()
    assert set(_ids(r["items"])) == {"cand_a", "cand_c", "cand_e"}


def test_skills_filter_requires_all_skills(api_client):
    pair = api_client.get("/candidates", params={"skills": "Python,FastAPI"}).json()
    assert set(_ids(pair["items"])) == {"cand_a", "cand_e"}  # must contain BOTH

    single = api_client.get("/candidates", params={"skills": "python"}).json()
    assert set(_ids(single["items"])) == {"cand_a", "cand_c", "cand_d", "cand_e"}


def test_shortlist_filter(api_client):
    yes = api_client.get("/candidates", params={"is_shortlisted": "true"}).json()
    assert _ids(yes["items"]) == ["cand_a"]
    no = api_client.get("/candidates", params={"is_shortlisted": "false"}).json()
    assert set(_ids(no["items"])) == {"cand_b", "cand_c", "cand_d", "cand_e"}


def test_combined_filters_and_logic(api_client):
    r = api_client.get(
        "/candidates",
        params={
            "target_role": "Backend Engineer",
            "min_experience": 2,
            "skills": "Python",
        },
    ).json()
    assert set(_ids(r["items"])) == {"cand_a", "cand_c", "cand_e"}


# --------------------------------------------- target_role/source OR lists ----
def test_target_role_or_list(api_client):
    r = api_client.get(
        "/candidates",
        params={"target_role": "Backend Engineer,Frontend Engineer"},
    ).json()
    assert set(_ids(r["items"])) == {"cand_a", "cand_b", "cand_c", "cand_e"}

    # A single value still behaves exactly as before.
    single = api_client.get(
        "/candidates", params={"target_role": "Backend Engineer"}
    ).json()
    assert set(_ids(single["items"])) == {"cand_a", "cand_c", "cand_e"}


def test_target_role_or_list_case_insensitive_and_duplicates(api_client):
    case_mixed = api_client.get(
        "/candidates",
        params={"target_role": "backend engineer,FRONTEND Engineer"},
    ).json()
    assert set(_ids(case_mixed["items"])) == {"cand_a", "cand_b", "cand_c", "cand_e"}

    dups = api_client.get(
        "/candidates",
        params={"target_role": "Backend Engineer,  backend  engineer "},
    ).json()
    assert set(_ids(dups["items"])) == {"cand_a", "cand_c", "cand_e"}


def test_source_or_list(api_client):
    r = api_client.get(
        "/candidates", params={"source": "Naukri,AngelList"}
    ).json()
    assert set(_ids(r["items"])) == {"cand_a", "cand_c", "cand_d", "cand_e"}

    single = api_client.get("/candidates", params={"source": "naukri"}).json()
    assert set(_ids(single["items"])) == {"cand_a", "cand_c", "cand_e"}


def test_or_lists_combine_with_and_across_categories(api_client):
    r = api_client.get(
        "/candidates",
        params={
            "target_role": "Backend Engineer,Frontend Engineer",  # OR
            "source": "Naukri,LinkedIn",  # OR
            "skills": "Python,FastAPI",  # ALL-of
            "min_experience": 2,
            "max_experience": 6,
        },
    ).json()
    # Roles {a,b,c,e} AND sources {a,c,e,b} AND Python+FastAPI {a,e} AND 2-6yrs {a,e}
    assert set(_ids(r["items"])) == {"cand_a", "cand_e"}


def test_missing_role_or_source_match_nothing_non_blocking(api_client):
    r = api_client.get(
        "/candidates", params={"target_role": "ML Engineer,Backend Engineer"}
    ).json()
    assert _ids(r["items"]) == ["cand_a", "cand_c", "cand_e"]


def test_skills_still_requires_all_skills_with_role_or(api_client):
    r = api_client.get(
        "/candidates",
        params={
            "target_role": "Backend Engineer,Data Engineer",
            "skills": "Python,PostgreSQL",
        },
    ).json()
    # Roles {a,c,e,d}; only Carol has both Python and PostgreSQL.
    assert _ids(r["items"]) == ["cand_c"]


def test_sort_by_experience_desc_with_stable_tie_break(api_client):
    r = api_client.get(
        "/candidates", params={"sort_by": "years_experience", "sort_order": "desc"}
    ).json()
    # 8 (carl) > 5 (alice) > 3 (dave) > 2 tie -> id asc (cand_b before cand_e)
    assert _ids(r["items"]) == ["cand_c", "cand_a", "cand_d", "cand_b", "cand_e"]


def test_sort_by_name_asc_case_insensitive(api_client):
    r = api_client.get("/candidates", params={"sort_by": "name"}).json()
    assert _ids(r["items"]) == ["cand_a", "cand_b", "cand_c", "cand_d", "cand_e"]


def test_sort_by_applied_date_desc(api_client):
    r = api_client.get(
        "/candidates", params={"sort_by": "applied_date", "sort_order": "desc"}
    ).json()
    assert _ids(r["items"]) == [
        "cand_a",  # 2026-09-01
        "cand_c",  # 2026-08-20
        "cand_e",  # 2026-07-10
        "cand_b",  # 2025-01-15
        "cand_d",  # 2024-06-05
    ]


def test_multi_column_sort_primary_then_secondary(api_client):
    # Primary: years_experience ASC; secondary: applied_date DESC for ties.
    # exp 2 tie (bob 2025, erika 2026) -> erika before bob.
    r = api_client.get(
        "/candidates",
        params={
            "sort_by": "years_experience,applied_date",
            "sort_order": "asc,desc",
        },
    ).json()
    assert _ids(r["items"]) == ["cand_e", "cand_b", "cand_d", "cand_a", "cand_c"]


def test_multi_column_sort_whitespace_and_case_normalized(api_client):
    # Tokens may have extra whitespace/case; still validated and applied.
    r = api_client.get(
        "/candidates",
        params={
            "sort_by": "years_experience,applied_date",
            "sort_order": "asc,desC",
        },
    ).json()
    assert _ids(r["items"]) == ["cand_e", "cand_b", "cand_d", "cand_a", "cand_c"]


def test_multi_column_sort_combines_with_filters(api_client):
    # Filter AND + multi-column sort priority preserved.
    r = api_client.get(
        "/candidates",
        params={
            "target_role": "Backend Engineer",
            "sort_by": "years_experience,applied_date",
            "sort_order": "asc,desc",
        },
    ).json()
    # Backend engineers: 5y alice (2026-09-01), 8y carol (2026-08-20),
    # 2y erika (2026-07-10).
    assert _ids(r["items"]) == ["cand_e", "cand_a", "cand_c"]


def test_multi_column_sort_last_pass_wins_priority(api_client):
    # Primary: applied_date DESC; secondary: years_experience ASC.
    r = api_client.get(
        "/candidates",
        params={
            "sort_by": "applied_date,years_experience",
            "sort_order": "desc,asc",
        },
    ).json()
    assert _ids(r["items"]) == ["cand_a", "cand_c", "cand_e", "cand_b", "cand_d"]


@pytest.mark.parametrize(
    "params",
    [
        # Mismatched number of fields/directions.
        {"sort_by": "name,applied_date", "sort_order": "asc"},
        {"sort_by": "name", "sort_order": "asc,desc"},
        # Duplicate sort field.
        {"sort_by": "name,name", "sort_order": "asc,desc"},
        # Invalid field in a multi-column list.
        {"sort_by": "name,not_a_real_column", "sort_order": "asc,desc"},
        # Invalid direction in a multi-column list.
        {"sort_by": "name,applied_date", "sort_order": "asc,up"},
        # Explicit empty sort input.
        {"sort_by": "", "sort_order": ""},
        {"sort_by": ",   ,", "sort_order": ",  ,"},
    ],
)
def test_invalid_multi_column_sort_returns_400(api_client, params):
    r = api_client.get("/candidates", params=params)
    assert r.status_code == 400
    assert "sort" in r.json()["detail"].lower()


def test_default_sort_is_name_asc(api_client):
    r = api_client.get("/candidates").json()
    assert _ids(r["items"]) == ["cand_a", "cand_b", "cand_c", "cand_d", "cand_e"]


@pytest.mark.parametrize(
    "params",
    [
        {"sort_by": "not_a_real_column"},
        {"sort_by": "__tablename__"},
        {"sort_order": "up"},
        {"sort_by": "years_experience", "sort_order": "sideways"},
    ],
)
def test_invalid_sort_returns_400(api_client, params):
    r = api_client.get("/candidates", params=params)
    assert r.status_code == 400
    assert "sort" in r.json()["detail"].lower()


@pytest.mark.parametrize(
    "params",
    [
        {"page": "0"},
        {"page": "-2"},
        {"page_size": "0"},
        {"page_size": "101"},
        {"min_experience": "-1"},
        {"max_experience": "-1"},
        {"min_experience": "5", "max_experience": "2"},
        {"is_shortlisted": "maybe"},
        {"skills": " , "},
        {"target_role": " , "},
        {"source": ",  "},
    ],
)
def test_invalid_filter_values_return_400(api_client, params):
    assert api_client.get("/candidates", params=params).status_code == 400


def test_non_numeric_pagination_is_422(api_client):
    assert api_client.get("/candidates", params={"page": "abc"}).status_code == 422


# ------------------------------------------------------------- detail ------
def test_candidate_detail(api_client):
    body = api_client.get("/candidates/cand_a").json()
    assert set(body.keys()) == CANDIDATE_FIELDS
    assert body["id"] == "cand_a"
    assert body["name"] == "Alice"
    assert body["years_experience"] == 5
    assert body["skills"] == ["Python", "FastAPI", "Docker"]
    assert body["is_shortlisted"] is True
    assert body["applied_date"] == "2026-09-01"


def test_candidate_detail_missing_returns_404(api_client):
    r = api_client.get("/candidates/does-not-exist")
    assert r.status_code == 404


# ---------------------------------------------------------- shortlisting ----
def test_shortlist_then_unshortlist_persists(api_client):
    r = api_client.patch("/candidates/cand_b", json={"is_shortlisted": True})
    assert r.status_code == 200
    assert r.json()["is_shortlisted"] is True

    persisted = api_client.get("/candidates/cand_b").json()
    assert persisted["is_shortlisted"] is True

    api_client.patch("/candidates/cand_b", json={"is_shortlisted": False})
    assert api_client.get("/candidates/cand_b").json()["is_shortlisted"] is False


def test_patch_returns_full_candidate(api_client):
    body = api_client.patch(
        "/candidates/cand_d", json={"is_shortlisted": True}
    ).json()
    assert set(body.keys()) == CANDIDATE_FIELDS
    assert body["id"] == "cand_d"
    assert body["is_shortlisted"] is True


def test_patch_missing_candidate_returns_404(api_client):
    r = api_client.patch("/candidates/nope", json={"is_shortlisted": True})
    assert r.status_code == 404


def test_patch_rejects_arbitrary_fields(api_client):
    r = api_client.patch(
        "/candidates/cand_a", json={"is_shortlisted": True, "name": "Hacked"}
    )
    assert r.status_code == 422
    # DB unchanged
    assert api_client.get("/candidates/cand_a").json()["name"] == "Alice"


def test_patch_requires_is_shortlisted(api_client):
    assert api_client.patch("/candidates/cand_a", json={}).status_code == 422
    assert (
        api_client.patch("/candidates/cand_a", json={"name": "X"}).status_code
        == 422
    )


def test_get_requests_do_not_mutate(api_client):
    snapshot = api_client.get("/candidates", params={"is_shortlisted": "false"}).json()
    api_client.get("/candidates")
    api_client.get("/candidates/cand_b")
    api_client.get("/candidates", params={"search": "python"})
    after = api_client.get("/candidates", params={"is_shortlisted": "false"}).json()
    assert [i["is_shortlisted"] for i in after["items"]] == [False] * len(snapshot["items"])


# -------------------------------------------------------------- OpenAPI -----
def test_openapi_exposes_expected_endpoints():
    schema = app.openapi()
    assert set(schema["paths"]) == {
        "/health",
        "/candidates",
        "/candidates/{candidate_id}",
        "/match",
    }
    match_post = schema["paths"]["/match"]["post"]
    assert match_post["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("MatchRequest")