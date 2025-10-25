# MyTrail Backend

## tree
```
backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Configuration management (supports Mock/API mode)
│   ├── api/routes.py        # HTTP routes
│   ├── models/              # Pydantic data models
│   └── services/
│       ├── map/             # Mapping services
│       │   ├── google_map_service.py    # Google Maps API integration
│       │   └── api_counter.py           # API call counter
│       └── route/           # Route generation services
│           ├── recall_service.py      # Candidate route recall
│           ├── ranking_service.py     # Baseline quality ranking
│           ├── reranking_service.py   # Diversity re-ranking
│           └── response_builder.py   # Response construction
```

## test

`cd backend` then `python test/test_`


FastAPI backend that powers the MyTrail experience. It now includes an OpenAI-backed natural language parser that converts multi-lingual user intent into structured `RouteCriteria` objects.

## Key Services
- `app/main.py` – FastAPI entry point; exposes `/api/v1/routes/query`, `/api/v1/routes/suggest`, `/parse`, and `/health` endpoints.
- `app/services/nlp/` – Preprocess → LLM parse → validate pipeline for converting free text into `RouteCriteria`.
- `app/services/route/` – Route generation, ranking, and response shaping.

## Configuration
Set an OpenAI API key (and optional model/base URL overrides) before using the parsing endpoint:
```bash
export OPENAI_API_KEY="sk-..."
# Optional overrides
export OPENAI_MODEL="o4-mini"
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

## Running Locally
```bash
cd backend
uvicorn app.main:app --reload
```

## Docker Compose
```bash
docker compose up --build
```
This launches the FastAPI backend on `http://localhost:8000` alongside a MongoDB instance on `mongodb://localhost:27017`.

### Development Mode (Hot Reload)
```bash
docker compose -f docker-compose.dev.yml up --build
```
This mounts the backend source for live code reloads while keeping MongoDB in a companion container. Re-run the command after changing dependencies so the image picks up updated `requirements.txt`.

## Tests
```bash
cd backend
pytest
```
