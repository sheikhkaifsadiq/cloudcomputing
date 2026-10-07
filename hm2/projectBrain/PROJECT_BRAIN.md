# PROJECT BRAIN

## Project Purpose
HM2: Convert HM1 (React + Supabase contacts app) into an AI CRUD agent demonstrating FastAPI, LangGraph, Gemini LLM tool calling, and Human-in-the-Loop (HITL) approval. University Cloud Computing assignment.

---

## Actual Verified Implementation (Updated 2026-10-06)

### LLM
- Model: **gemini-flash-lite-latest** via `langchain-google-genai`
- Configurable via `GEMINI_MODEL` in `.env`
- Verified: HTTP 200 confirmed, tool calls observed in live run

### Backend
- Framework: **FastAPI**
- Entry: `backend/main.py`
- Endpoints: `/api/health`, `/api/chat`, `/api/hitl/approve`, `/api/hitl/decline`, `/api/hitl/details`, `/api/history`

### Agent Orchestration
- Library: **LangGraph**
- Graph: `process_message → safety_gate → execute_safe_tools | execute_destructive_tools`
- Safety invariant: If LLM returns `get_records` + `delete_record` in one response, `delete_record` is stripped and only `get_records` runs first
- HITL mechanism: `interrupt(...)` pauses destructive node; resumed via `Command(resume=...)`
- Checkpointing: `MemorySaver` — **in-memory only, not durable across backend restarts**

### CRUD Tools (`backend/crud_tools.py`)
- `create_record` — validates required fields: name, department, email, phone, position
- `get_records` — entity allow-list enforced
- `update_record` — safety check: must be exactly 1 match before update
- `delete_record` — safety check: must be exactly 1 match; 0 → not found, 2+ → ambiguous
- Entity allow-list: only `employees` is accessible to the LLM

### Database
- Provider: **Supabase** — same project as HM1 (`kmofepgulnovqrylsrxm.supabase.co`)
- Tables required:
  - `employees` (id, name, department, email, phone, position, created_at, updated_at)
  - `operation_history` (id, conversation_id, timestamp, operation, entity, target, status, result)
- Service role key used server-side only — never exposed to frontend

### Frontend
- Framework: React 19 + Vite
- Style: Minimalistic neumorphism, dark-ish theme
- Layout: Sidebar (history) + Chat (messages + approval card)
- Communicates only with FastAPI — no direct Supabase calls for CRUD
- Does not use `dangerouslySetInnerHTML` or `prompt(...)`

---

## Architecture Caveats
- `MemorySaver` is in-memory. If the backend process restarts, all pending LangGraph workflow states are lost. This is acceptable for an assignment demonstration.
- Supabase stores all employee data and operation history persistently.
- Ambiguous delete (2+ matches) is caught both by the delete_record tool and by the LLM system prompt.
- History `target` field uses human-readable `Name · Department` format.

---

## File Structure
```
backend/         FastAPI + LangGraph + CRUD tools
frontend/        React/Vite UI
projectBrain/    Docs: NON_EDITABLE_RULES.md, PROJECT_BRAIN.md, TASK_LOG.md, SUPABASE_SETUP.md
tests/           End-to-end test scripts
scripts/         Utility scripts
.env             Secrets (not committed)
.gitignore       Excludes venv, __pycache__, dist, node_modules
```
