# AI Customer Support Agent with Long-Term Memory

A full-stack customer support agent built with React, FastAPI, SQLite, Ollama, Qwen3 8B, and Hindsight.

The goal is to provide support conversations that can persist useful customer context beyond a single conversation.

## Architecture

- Frontend: React + Vite
- Backend: FastAPI
- Database: SQLite + SQLAlchemy
- LLM: Ollama + Qwen3 8B
- Long-term memory: Hindsight
- Testing: Pytest

```text
React / Vite
     |
     v
FastAPI API
   /     \
  v       v
SQLite   Ollama
          |
       Qwen3 8B

FastAPI <----> Hindsight
                 |
          Long-term memory
