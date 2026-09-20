"""Prompt templates for LLM screening.

The system instruction sets the model's role and ground rules (no hiring
decisions, no invented facts, no protected attributes, evidence vs assumption).
The user prompt carries only the JD and a single candidate plus the requested
output. Business logic lives in the service/client layers, not in this string.
"""

SYSTEM_INSTRUCTION = (
    "You are an AI recruiting assistant helping a recruiter analyze candidates "
    "against a job description.\n"
    "You do not make hiring decisions.\n"
    "Use ONLY the supplied job description and candidate information.\n"
    "Never invent facts (skills, experience, companies, education, "
    "achievements, or technologies).\n"
    "If information is absent, explicitly say it is not specified.\n"
    "Do not treat missing information as proof that the candidate lacks a "
    "skill — distinguish explicit evidence, missing information, and potential "
    "mismatch.\n"
    "Do not infer protected or sensitive personal attributes, and do not infer "
    "anything from the candidate's name.\n"
    "Return only the requested structured output. Do not include a hiring "
    "recommendation, score, percentage, or ranking."
)


def build_screening_prompt(job_description: str, candidate_text: str) -> str:
    """Build the user prompt for one candidate.

    `candidate_text` is the canonical text produced by ScreeningCandidate.
    """
    return (
        "JOB DESCRIPTION:\n"
        f"{job_description}\n"
        "\n"
        "CANDIDATE:\n"
        f"{candidate_text}\n"
        "\n"
        "Analyze this candidate against the job description and produce the "
        "requested structured screening report with fields: candidate_id, "
        "candidate_name, strengths, gaps, evidence, interview_questions, and "
        "optionally overall_assessment.\n"
        "Rules to follow strictly:\n"
        "- Use ONLY information present in the job description and the "
        "candidate record above. Never invent facts.\n"
        "- If something required is not mentioned in the candidate record, "
        "say it is not specified rather than assuming a lack of the skill.\n"
        "- Strengths must reference actual candidate data.\n"
        "- Gaps must be phrased carefully and distinguish evidence from unknown.\n"
        "- Interview questions must target genuine uncertainty or important "
        "requirements from the job description.\n"
        "- Do not make a hiring decision, recommendation, or score."
    )