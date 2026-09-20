# AI Screening Pipeline

How a job description becomes a per-candidate screening report, and why it is
built this way.

## Pipeline

```
                  1x JD embedding API call
  JD ───────────► GeminiEmbeddingService ──► vec0 KNN ──► top-K RankedCandidate (by distance)

                                                       │
                                                       ▼
                                              RetrievalService output
                                    (candidates + cosine distance, lower = closer)

                                                       │
                                                       ▼  K LLM calls (one per candidate)
                                    ScreeningService ──► GeminiLLMClient ──► Gemini LLM
  (validated JD + canonical candidate,            │
   system + user prompt, response_schema)          ▼
                                    ScreeningReport (Pydantic-validated)

                                                       │
                                                       ▼
                            MatchAndScreenResult: retrieved + per-candidate outcomes
```

Modules:

| Concern | Module |
|---|---|
| Retrieval (embed + vec0 + top-K) | `app/services/retrieval.py` |
| LLM structured-output adapter | `app/services/llm_client.py` |
| Prompt construction | `app/services/prompts.py` |
| Canonical candidate input | `app/services/screening_input.py` |
| Screening (validate → prompt → LLM → report) | `app/services/screening_service.py` |
| Orchestration (compose retrieval + screening) | `app/services/orchestration.py` |

## Why retrieval and screening are separate

- Different failure modes: no embeddings indexed (retrieval) vs. LLM outage or
  malformed output (screening). Separate services keep errors typed and
  localized.
- Different test shapes: retrieval is tested with embedder stubs + sqlite-vec;
  screening is tested with LLM mocks. Neither test needs the other's stack.
- Different cost profiles: retrieval is one embedding call; screening is K LLM
  calls. You may want to screen fewer/more candidates than you retrieve.
- Boundaries keep the LLM from "helping" with math (see below) and stop
  vector internals from leaking into the prompt.

## Why the LLM never produces scores/hiring decisions

A cosine distance is a retrieval artifact, not a fit judgment. The pipeline
therefore never converts distance into a "match percentage", "score", or
"confidence", and never sends distance to the LLM. The screening prompt and
schema forbid hiring recommendations, scores, and rankings: the recruiter owns
the decision. Screening output is evidence-based (`strengths`, `gaps`,
`evidence`, `interview_questions`), with missing information labeled "not
specified" rather than assumed absent.

## What is sent to the LLM (and what is not)

Sent: `candidate_id`, `name`, `target_role`, `years_experience`, `source`,
`skills`, `notes` + the JD text.

Not sent: `is_shortlisted`, `applied_date`, embedding vectors, sqlite-vec
data, database/ORM internals. The prompt includes name-explanation and
anti-invention rules (no protected attributes, no inference from names).

## One LLM call per candidate

Chosen over one multi-candidate prompt because it gives per-candidate error
isolation, easier validation and retry, and simpler per-candidate
presentation. Trade-off: cost scales linearly with candidates.

## Cost (top_k = K)

- 1 JD embedding API call
- K LLM generate calls (screening)

Table search/filter/sort/shortlist/list endpoints never call the LLM.

## Partial failures

`screen_candidates` returns one explicit outcome per candidate, in order:
`ScreeningSuccess(candidate_id, report)` or `ScreeningFailure(candidate_id,
error_type, message)`. A failed candidate is never given a fake report, and a
failure does not stop the rest of the batch.

## Error model

`ScreeningError` hierarchy in `app/services/errors.py`:

- `ScreeningConfigurationError` — missing/blank API key or model
- `ScreeningApiError` — network, auth, rate limit, timeout, 5xx
- `ScreeningResponseError` — malformed JSON / Pydantic validation failure
- `ScreeningInputError` — empty JD, invalid candidate

Messages never include the API key. SDK exceptions are wrapped with their type
name (`APIError`, `ClientError`, `ServerError`, `httpx.TimeoutException`, …)
for diagnosis.

## Structured output mechanism

`GeminiLLMClient.generate_structured` calls
`models.generate_content(model, contents, config)` with
`config.response_mime_type="application/json"`, `config.response_schema=<pydantic
model>` and `config.system_instruction=<str>`. The SDK returns
`response.parsed` as a validated Pydantic instance.

The SDK silently swallows `JSONDecodeError`/`ValidationError` and leaves
`parsed=None` (verified in the installed `google-genai` 2.24.0). The client
therefore treats a missing `parsed` as a malformed result and re-validates the
raw `response.text` strictly (isolated in `_parse_structured`), raising
`ScreeningResponseError` on failure. Parsing lives in exactly one place.

## Retry

Transient API failures retried at most `max_retries` (a very small configurable
count, default 1). Configuration and response-shape failures are never retried.

## Real API execution

All tests mock the LLM (and the embedder); there are zero live Gemini calls in
the suite. Live runs (`python -m app.services.orchestration -j "..." -k 5`)
require `GEMINI_API_KEY` in `.env`; run them manually once the key is
configured.