# Recruitment Triage

A full-stack recruiter workflow for browsing, filtering, shortlisting, and AI-matching candidates against job descriptions — built for GCCX Global.

## What it does

A recruiter lands on a candidate table, narrows the pool with deterministic filters and multi-column sorting, shortlists promising profiles, and can paste a job description to have the closest candidates retrieved and screened with AI into structured, evidence-based reports. AI ranks and describes — the recruiter decides.

## Key features

- **Candidate table** with server-side pagination and multi-column sorting (priority-ordered, stable tie-breaking)
- **Search** across name, target role, notes, and skills
- **Filters** — target role, source, skills, experience range, and shortlist status; AND-combined, with multi-select within role/source and all-skills-required semantics
- **Active filter & sort chips** that reflect the applied query state
- **Shortlist / star** action, persisted to the database via the candidate API
- **Candidate details drawer** with notes, skills, and profile metadata
- **AI Match results view** — a dedicated in-app workflow with per-candidate similarity and collapsible screening reports
- **Responsive**, GCCX-styled UI (ivory background, near-black typography, green accent)

## AI matching

```
Job Description
     │  Gemini embedding (1 call)
     ▼
sqlite-vec (vec0) KNN ▸ top-K candidates by cosine distance
     │  one Gemini screening call per candidate (default 5)
     ▼
structured screening report (Pydantic-validated)
```

What the AI does:

- Embeds the job description once and retrieves the top-K candidates by cosine distance (lower = closer).
- Screens each retrieved candidate into a structured report: overall assessment (when provided), strengths, gaps, evidence, and interview questions.

What it deliberately does **not** do:

- **No hiring decision, score, or recommendation** — the prompt forbids percentages, rankings, and verdicts. The recruiter stays in control.
- **No natural-language "chat with candidates"** — the LLM is used only where semantic understanding adds value.
- **No LLM on the table view** — filtering, sorting, and shortlisting are deterministic and never call the AI.

Candidate embeddings encode only the semantic fit signal — target role, years of experience, skills, and notes. Recruiter/administrative fields (shortlist state, applied date) are deliberately excluded.

Inside the API, the retrieval result remains a raw cosine distance and ranking is by actual distance. The recruiter view renders a simple "Similarity %" derived from that distance for display only — not a match probability.

## Architecture

```
frontend (React + Vite)
     │  REST / JSON (typed API client)
     ▼
FastAPI
     │
     ├── SQLite      candidate records, shortlist state
     └── sqlite-vec  candidate embeddings (vec0 virtual table)
     │
     ▼
Gemini API          embeddings + structured screening output
```

Endpoints: `GET /candidates` (search, filters, multi-column sort, pagination), `GET/PATCH /candidates/{id}` (details and shortlist), `POST /match` (JD → retrieval → screening), `GET /health`.

The frontend talks only to the backend API — never the database. Gemini credentials live server-side in `.env` and are never shipped to the browser. Embeddings are stored next to the candidate rows in the same SQLite file, so there is no separate vector database to run or keep in sync.

## Engineering decisions

- **Deterministic recruiter operations.** Role, source, skills, experience, sorting, and shortlisting are plain backend queries — predictable, cheap, and testable. The LLM is never involved in ordinary table operations.
- **sqlite-vec instead of a vector database.** For this corpus, embeddings coexist with candidate rows in one SQLite database — no second service, no cross-store consistency. Retrieval sits behind a small repository interface, keeping the door open to a larger store if the dataset ever outgrows it.
- **One screening call per candidate.** Isolates failures, simplifies retries, and validates output per candidate. A failed screening surfaces as an explicit error — never a fabricated report.
- **Structured AI output.** The LLM response is validated against a Pydantic schema before it can reach the frontend.
- **Typed failure handling.** Embedding/vector and screening errors are distinct, typed exceptions; transient API failures get bounded retries.
- **Recruiter in the loop.** AI supplies evidence, gaps, and interview questions — the human makes the call.

## Tech stack

| Layer      | Technology                                              |
| ---------- | ------------------------------------------------------- |
| Frontend   | React 19, TypeScript, Vite, Tailwind CSS, shadcn/radix, TanStack Table, Phosphor icons, sonner |
| Backend    | Python, FastAPI, Pydantic, SQLAlchemy                   |
| Storage    | SQLite + sqlite-vec                                     |
| AI         | Google Gemini (`google-genai`): embeddings + structured output |
| Testing    | pytest (backend); oxlint, `tsc`, Vite build (frontend)  |

## Testing & build

- **Backend — 171 tests passing.** Covers filtering/sorting/validation, shortlist persistence, the vector index, screening schema validation, and the `/match` contract. Gemini is mocked throughout, so the suite never touches the network.
- **Frontend — `npm run lint` and `npm run build` (TypeScript + Vite) both pass.** (A few pre-existing oxlint warnings remain.)
- The AI pipeline was validated end-to-end against the live Gemini API during development, with real embeddings generated for all 48 candidates.

## Running locally

Prerequisites: Python 3.10+, Node.js 20.19+ (Vite 8 requires `^20.19.0 || >=22.12.0`).

**Backend** (terminal 1) — from the repository root:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000
```

**Frontend** (terminal 2) — from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The backend runs on http://localhost:8000 (allowed by default CORS; override with `VITE_API_BASE_URL` in `frontend/.env.development`).

**Enabling AI matching** — requires a Gemini API key applied as `GEMINI_API_KEY` (and, optionally, `GEMINI_LLM_MODEL`, `GEMINI_EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`) in `.env` — from the repository root:

```bash
cp .env.example .env                       # add GEMINI_API_KEY
cd backend
source ../.venv/bin/activate               # if the venv is not already active
python -m app.db.seed                      # load the 48 candidates (idempotent)
python -m app.db.embed_candidates          # generate + index embeddings (idempotent)
```

All non-AI features — table, search, filters, sorting, shortlist, details — work without a key.

## Project structure

```
backend/
  app/
    api/routes/   candidates, match, health
    services/     retrieval, screening, embedding, orchestration (the AI pipeline)
    db/           database, seed, embed_candidates
    schemas/      Pydantic contracts (API + ScreeningReport)
    core/config.py  env-driven settings (Gemini secrets stay server-side)
  tests/          171 tests
frontend/
  src/
    pages/        CandidatesPage (candidate list ⇄ AI Match results view)
    components/
      candidates/ table, filters, search, shortlist, details drawer
      matching/   AI Match dialog, results view, screening report
      ui/         shadcn/radix primitives
    lib/          typed API client, types, formatting
data/
  candidates.json  48 mock candidate records
```

## Scope notes

- The candidate data is synthetic mock data created for this case study (see `data/README.md`).
- `backend/recruitment.db` is gitignored, so a fresh checkout must run the seed and embed steps above before using AI matching.
- Screening reports are evidence-based and never a hiring recommendation; the shortlist remains the recruiter's persisted signal.
