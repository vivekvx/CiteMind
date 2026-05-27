# AGENTS.md

## Project Rules

- Keep changes minimal and scoped to the requested phase.
- Do not rewrite working backend or frontend files.
- Do not delete `LICENSE`.
- Do not add auth or extra features unless requested.
- Use `backend/.venv/bin/python` and `backend/.venv/bin/pip` for backend checks.

## Setup Commands

```bash
cd /Users/vivek/CiteMind/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

```bash
cd /Users/vivek/CiteMind/frontend
npm install
```

## Backend Run Command

```bash
cd /Users/vivek/CiteMind
backend/.venv/bin/python -m uvicorn backend.app.main:app --reload
```

## Frontend Run Command

```bash
cd /Users/vivek/CiteMind/frontend
npm run dev
```

## Docker Command

```bash
cd /Users/vivek/CiteMind
docker compose up --build
```

## Test/Check Commands

```bash
cd /Users/vivek/CiteMind
PYTHONPYCACHEPREFIX=/private/tmp/citemind-pycache backend/.venv/bin/python -m compileall backend/__init__.py backend/app
backend/.venv/bin/python -c "from backend.app.main import app; print(app.title)"
```

```bash
cd /Users/vivek/CiteMind/frontend
npm run build
```
