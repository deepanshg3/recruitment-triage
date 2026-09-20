# GCCX AI Full-Stack Engineer Intern — Case Study Starter Kit

This is everything you need to start Task 1 of the Round 1 case study. It's deliberately
minimal — there's no scaffold code to fight with, because the point of this round is your
decisions, not your boilerplate.

## What's here

- `candidates.json` — 48 mock candidate records. This is fake data, generated for this
  exercise only (not real GCCX candidates). Each record has:
  - `id`, `name`, `target_role`, `years_experience`, `source`, `skills` (array), `notes`
    (free text), `applied_date`
- This README.

## What you build on top of it

See **Task 1 — Build: Candidate Triage Tool** in the case study brief for the full spec.
In short: a backend API, a minimal frontend, a real database (SQLite is fine — load
`candidates.json` into it however you like), and one feature that calls an LLM API for
real (e.g. a one-line fit summary generated from the `notes` field, or semantic search
across `notes`).

Use whatever language, framework, and AI tooling you'd normally reach for. There is no
"correct" stack — the JD is explicitly language- and framework-agnostic, and so is this
exercise.

## A note on the data

It's intentionally a little messy — some notes are thin, some candidates look stronger
than others, source quality varies. That's realistic, and also part of the point: don't
spend your limited time budget trying to "clean up" the mock data before you start
building. Treat it the way you'd treat a real, slightly imperfect dataset handed to you
on day one.
