# ZooLingo — AGENTS.md

## Project Overview

ZooLingo is an open-source (MIT) voice-first AI agent that translates animal vocalizations into human language, built for Techfest IIT Bombay + SARVAM AI Hackathon.

**Live Demo:** https://zoolingo-deploy.vercel.app  
**Current Deploy:** https://zoolingo-local.vercel.app  
**GitHub:** https://github.com/JSR2406/zoolingo-

## Tech Stack

- **Backend:** FastAPI + Python 3.11, SQLite (local dev), :memory: (Vercel serverless)
- **Frontend:** React 18 + Vite + Tailwind + Framer Motion
- **AI:** SARVAM Bulbul v3 TTS + Sarvam-105B LLM + YAMNet/TensorFlow (optional)
- **Database:** SQLite via petcare/ (local), Supabase (production, optional)
- **Deploy:** Vercel (serverless Python + static frontend)

## Ponytail Skill (Lazy Senior Dev Mode)

This project uses the **Ponytail** skill for OpenCode. Before writing code:

1. Read the task and the code it touches. List every place your change must reach.
2. Skip features/options nobody asked for. Name them in one line.
3. Reuse existing code in this codebase first (stdlib, platform, installed deps).
4. Take the smallest change that fully works.
5. New non-trivial logic leaves one small test or assert-based self-check.
6. End your reply with: what you skipped/did not check, and any risk.

Switch level: `/ponytail lite|full|ultra|off`

## Key Directories

- `backend/app.py` — FastAPI app entrypoint (Vercel serverless via `api/index.py`)
- `backend/api/requirements.txt` — Python deps for Vercel serverless runtime
- `backend/petcare/` — Pet care hub: database, router, expert engine, schemas
- `backend/services/` — SARVAM TTS/LLM, YAMNet classifier, audio processor, Murf, Deepgram
- `frontend/src/` — React/Vite frontend (App.jsx, pages/, components/, layout/)
- `vercel.json` — Vercel deployment config (version 2, builds for Python + static)

## Environment Variables (Vercel Dashboard)

Set in **Vercel Dashboard → Project → Settings → Environment Variables:**

| Variable | Required | Notes |
|----------|----------|-------|
| `SARVAM_API_KEY` | ✅ Yes | Primary TTS |
| `ELEVENLABS_API_KEY` | ✅ Yes | Demo sound effects |
| `MURF_API_KEY` | ⚠️ Optional | TTS fallback |
| `ENVIRONMENT` | ✅ Yes | `production` |
| `VERCEL` | ✅ Yes | `1` |
| `ALLOWED_ORIGINS` | ✅ Yes | `https://zoolingo-local.vercel.app` |
| `SUPABASE_URL` | ⚠️ Optional | For Supabase auth + pet data |
| `SUPABASE_SERVICE_ROLE_KEY` | ⚠️ Optional | Supabase service role |
| `SUPABASE_ANON_KEY` | ⚠️ Optional | Supabase anon key (client-side) |
| `SUPABASE_JWT_SECRET` | ⚠️ Optional | Supabase JWT secret (backend verification) |

## Without Supabase (Demo Mode)

If `SUPABASE_JWT_SECRET` is not set, the backend runs in **demo mode** with a default user (`demo_user_001`). Petcare sections (Dashboard, Pets, Health, Care Schedules, Vet Directory, Expert) work with seeded demo data (Buddy the dog, Mia the cat).

## With Supabase (Production Auth)

1. Create a project at https://supabase.com
2. Run the schema from `backend/petcare/database.py` (`_SCHEMA`) in Supabase SQL editor
3. Set `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET` in Vercel
4. Client-side: use `supabase-js` for signup/login; backend verifies JWT via `SUPABASE_JWT_SECRET`

## Deploy

```powershell
cd "E:\ coding\zoolingo-local"
vercel --prod --force
```

## Test Endpoints

- `GET /health` — service health
- `GET /api/languages` — supported languages + voices
- `GET /api/petcare/dashboard` — pet dashboard (demo user)
- `GET /api/petcare/pets` — list pets
- `GET /api/petcare/pets/{pet_id}/care-schedules` — care schedules for a pet
- `POST /api/process-audio` — translate animal audio (requires auth)
