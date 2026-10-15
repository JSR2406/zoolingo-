# Implementation Plan: ZooLingo → PetCare Hub (Pet Care & Communication Platform)

## Overview

Turn the existing ZooLingo animal-sound translator (FastAPI + React/Vite) into a
full-fledged **pet care + communication platform**: pet profiles, health &
vaccination records, care scheduling/reminders, vet directory, weight tracking,
and a **personal pet care expert assistant** (chat UI + rule-based triage +
care advice engine), all wrapped around the existing audio translation pipeline
(YAMNet/AudioSet → animal+emotion → NLP + SARVAM LLM translation → SARVAM TTS).

## Architecture Decisions

- **Database:** SQLite via SQLAlchemy 2.x (stdlib-friendly, zero-setup, works
  locally + Docker). Models follow the OpenVPM / Open Vet Format (OVF) pet-health
  schema patterns: `Pet`, `HealthRecord`, `VaccinationRecord`, `WeightLog`,
  `CareSchedule`, `VetContact`, `Conversation`.
- **Backend:** Keep existing `app.py` pipeline untouched. Add a new package
  `backend/petcare/` with its own FastAPI `APIRouter` mounted under `/api/petcare/*`.
  New service `backend/petcare/expert_engine.py` = rule-based pet-care expert
  (symptom triage → emergency/urgent/routine, vaccination-due logic, feeding/
  weight guidance, care schedule advice, all-animal advice KB). Optionally call
  Sarvam LLM when available; rule engine is the offline fallback so the platform
  works with zero extra keys.
- **Frontend:** Add `react-router-dom`, a new app shell with sidebar navigation
  (Dashboard, Pets, Health, Care Schedules, Vet Directory, Expert, Translate).
  Reuse the existing glass/neon design system (Tailwind + framer-motion) and all
  existing translation components. New pages live in `frontend/src/pages/`.
- **Persistence:** `backend/data/zoolingo.db` (gitignored). Seed with 2 demo
  pets + sample records on first boot so the UI is instantly demonstrable.
- **Deploy:** Vercel Python ― SQLite is file-backed; on serverless it degrades to
  in-memory per instance (documented). Local Docker/dev is the primary target.

## Task List

### Phase 1: Backend foundation
- [ ] Task 1: SQLAlchemy models + engine/session + auto-create + seed (Pet, HealthRecord, VaccinationRecord, WeightLog, CareSchedule, VetContact, Conversation)
- [ ] Task 2: `backend/petcare/router.py` — CRUD endpoints for pets, health records, weight logs, care schedules, vet contacts
- [ ] Task 3: `backend/petcare/expert_engine.py` — rule-based triage + advice KB + vaccination-due + feed/weight guidance
- [ ] Task 4: Expert chat endpoint (REST `/api/petcare/expert/advice` + SSE stream `/api/petcare/expert/chat`) with optional Sarvam LLM
- [ ] Task 5: Mount router in `app.py`; pytest coverage for routes + engine

### Phase 2: Frontend shell + care UI
- [ ] Task 6: Add react-router-dom, App shell with sidebar layout, routes
- [ ] Task 7: Dashboard page (per-pet health snapshot, due vaccinations, upcoming care)
- [ ] Task 8: Pets page (profile cards + add/edit pet)
- [ ] Task 9: Health page (vaccinations + weight log + health records entries)
- [ ] Task 10: Care Schedules page (feeding/grooming/medication/reminders)
- [ ] Task 11: Vet Directory page (find/save vet contacts)
- [ ] Task 12: Pet Care Expert page (chat UI with streaming, triage badges, care advice cards)
- [ ] Task 13: Translate page (wrap existing translation + audio pipeline, per-pet context)

### Phase 3: Verification & polish
- [ ] Checkpoint: backend pytest passes, frontend `npm run build` succeeds
- [ ] Checkpoint: manual E2E — seed pets, run expert advice, stream chat, translate audio
- [ ] Task 14: README/docs update (petcare endpoints, setup, DB notes)

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| SQLite non-persistent on Vercel RN | Med | Document; primary target is Docker/local; keep DB layer swappable to Postgres/Supabase |
| Sarvam LLM key flaky/unavailable | Med | Rule-based expert engine is the default path; LLM only when key + health pass |
| Many new UI pages | High | Reuse design system, one shared `api.js` client, small reusable components |
| React router on Vercel catch-all | Low | Vercel catch-all already rewrites to index.html — compatible |

## Open Questions
- Auth/multi-user: out of scope for this iteration (single household), flagged for next.