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
 
# Installation & Setup

This project is a customer support AI agent built with:

* **Frontend:** React + Vite
* **Backend:** FastAPI + Python
* **Database:** SQLite
* **LLM:** Qwen3 8B
* **Local LLM Runtime:** Ollama
* **Long-term Memory:** Hindsight

The following instructions explain how to run the project on **macOS, Linux, and Windows**.

---

## Prerequisites

Before starting, install:

* Git
* Python 3.10+
* Node.js 18+
* npm
* Ollama

Check that they are installed:

```bash
git --version
python --version
node --version
npm --version
ollama --version
```

---

# 1. Clone the Repository

Open Terminal, Command Prompt, or PowerShell:

```bash
git clone https://github.com/charansaiteja-cloud/AI-AGENT.git
cd AI-AGENT
```

---

# 2. Install Ollama

Ollama is used to run the Qwen3 model locally.

## macOS

Install Ollama from the official website and then verify:

```bash
ollama --version
```

Start Ollama if it is not already running:

```bash
ollama serve
```

Open another terminal and download the model:

```bash
ollama pull qwen3:8b
```

---

## Linux

Install Ollama using the official installation method:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Verify the installation:

```bash
ollama --version
```

Start Ollama:

```bash
ollama serve
```

In another terminal:

```bash
ollama pull qwen3:8b
```

---

## Windows

Download and install Ollama for Windows.

After installation, open **PowerShell** and verify:

```powershell
ollama --version
```

Download the Qwen3 8B model:

```powershell
ollama pull qwen3:8b
```

Test the model:

```powershell
ollama run qwen3:8b
```

---

# 3. Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

## macOS / Linux

Create a Python virtual environment:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Windows

Create a virtual environment:

```powershell
python -m venv venv
```

Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate again:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

---

# 4. Configure Environment Variables

Create a `.env` file inside the backend directory if the project requires environment variables.

Example:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
```

Add any required Hindsight configuration according to your local setup.

**Do not commit API keys, passwords, or other secrets to GitHub.**

---

# 5. Initialize the Database

The project uses SQLite for application data.

From the backend directory, run the database initialization command used by the project.

For example:

```bash
python init_db.py
```

If database initialization is handled automatically when the FastAPI application starts, this step can be skipped.

---

# 6. Start the Backend

Make sure the Python virtual environment is activated.

Run:

```bash
uvicorn main:app --reload
```

The FastAPI backend should be available at:

```text
http://127.0.0.1:8000
```

API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

Keep this terminal running.

---

# 7. Start the Frontend

Open a **new terminal**.

Navigate to the frontend directory:

```bash
cd frontend
```

Install Node.js dependencies:

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

Open that address in your browser.

---

# 8. Running the Complete Application

You normally need the following services running:

### Terminal 1 — Ollama

```bash
ollama serve
```

### Terminal 2 — FastAPI Backend

```bash
cd backend
```

Activate the virtual environment and run:

```bash
uvicorn main:app --reload
```

### Terminal 3 — React/Vite Frontend

```bash
cd frontend
npm run dev
```

Then open the frontend URL shown by Vite.

---

# 9. Verify Ollama

Before using the application, make sure Qwen3 8B is available:

```bash
ollama list
```

You should see:

```text
qwen3:8b
```

You can also test it directly:

```bash
ollama run qwen3:8b
```

---

# 10. Running Tests

Backend tests are written using Pytest.

From the backend directory:

```bash
pytest
```

For more detailed output:

```bash
pytest -v
```

---

# 11. Building the Frontend

To create a production build:

```bash
npm run build
```

The generated files will be placed in the Vite build output directory.

To preview the production build locally:

```bash
npm run preview
```

---

# 12. Troubleshooting

## Ollama connection error

Make sure Ollama is running:

```bash
ollama serve
```

Then verify:

```bash
ollama list
```

Make sure the required model is installed:

```bash
ollama pull qwen3:8b
```

---

## Python dependency error

Make sure the virtual environment is activated and reinstall dependencies:

```bash
pip install -r requirements.txt
```

---

## Frontend dependency error

Delete the existing Node modules and reinstall:

```bash
rm -rf node_modules
npm install
```

On Windows PowerShell:

```powershell
Remove-Item -Recurse -Force node_modules
npm install
```

---

## Port already in use

If port `8000` is already being used, start FastAPI on another port:

```bash
uvicorn main:app --reload --port 8001
```

For Vite, you can specify another port:

```bash
npm run dev -- --port 5174
```

---

# Architecture

```text
                    ┌─────────────────────┐
                    │   React + Vite      │
                    │      Frontend       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    FastAPI Backend  │
                    └──────┬────────┬─────┘
                           │        │
                ┌──────────┘        └──────────┐
                ▼                              ▼
        ┌──────────────┐                ┌──────────────┐
        │    SQLite    │                │   Hindsight  │
        │ App / State  │                │ Long-term    │
        │              │                │ Memory       │
        └──────────────┘                └──────────────┘
                                              
                           ┌───────────────────┐
                           │      Ollama       │
                           │                   │
                           │     Qwen3 8B      │
                           └───────────────────┘
```

---

# Quick Start

For users who already have the prerequisites installed:

```bash
git clone https://github.com/charansaiteja-cloud/AI-AGENT.git
cd AI-AGENT

cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Make sure Ollama is running with:

```bash
ollama serve
```

and Qwen3 8B is installed:

```bash
ollama pull qwen3:8b
```

---
## Demo

🎥 [View the Demo Video — brag.mp4](docs/demo/brag.mp4)

The demo showcases the customer support workflow, local Qwen3 8B inference, persistent long-term memory with Hindsight, attachment handling, and the web interface.

