# HM2 — AI CRUD Agent (React + FastAPI + LangGraph + Gemini + Supabase)

Converts the HM1 contacts app into an assignment-grade AI CRUD agent.  
Natural language → Gemini LLM → LangGraph agent → tool calling → Supabase → HITL approval.

## Architecture

```
React (Vite)
    ↓ /api/chat
FastAPI
    ↓
LangGraph workflow
    ↓
Gemini Flash Lite Latest (tool calling)
    ↓
CRUD Tools → Supabase PostgreSQL
    ↑
HITL interrupt() → React approval UI
    ↓
Command(resume=...) → delete_record
```

## Quick Start

### 1. Database Setup

Open the **same Supabase project used by HM1** and run the SQL from `projectBrain/SUPABASE_SETUP.md` in the SQL Editor.

### 2. Environment

Copy `.env.example` to `.env` and fill in:

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-flash-lite-latest
```

### 3. Backend

```bash
python -m venv venv
venv\Scripts\activate    # Windows
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

## Features

- **Natural Language CRUD** — type commands like "Show all HR employees" or "Delete Ali Ahmed from IT"
- **Human-in-the-Loop (HITL)** — delete operations pause for explicit user approval
- **Ambiguity Handling** — multiple matches → clarification requested; zero matches → not found
- **Add Details** — if a delete is paused and you provide more context, the LLM re-evaluates
- **Operation History** — all CRUD operations logged to Supabase with status

## Project Structure

```
backend/         FastAPI + LangGraph agent + CRUD tools
frontend/        React/Vite neumorphic AI chat interface
projectBrain/    Architecture docs, rules, setup guide, task log
tests/           End-to-end verification scripts
scripts/         Utility scripts (model checker, batch runner)
.env             Runtime secrets (not committed)
.env.example     Template for required variables
```

## Notes

- `MemorySaver` is used for LangGraph checkpointing (in-memory, assignment scope).  
  Pending workflow state is lost if the backend restarts.  
  Supabase stores all persistent data.
