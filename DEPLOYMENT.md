# Deployment (Docker)

This project is designed to be deployed per-client as an isolated container.

## Prereqs
- Docker + Docker Compose

## Configure

```bash
cd qa_bot
cp .env.example .env
# edit .env and set OPENAI_API_KEY at minimum
```

Key variables:
- `OPENAI_API_KEY` (required for Vision)
- `PETER_INTERNAL_DOMAIN` (used for internal-only email policy)
- `PETER_ALWAYS_CC` (comma-separated list)

## Run

```bash
docker compose up -d --build
```

## Data persistence
Data is stored in `./data` (mounted into the container at `/app/data`):
- `qa.db`
- `QA_ROOT/SITES/...`

Backups: snapshot/copy the entire `data/` folder.

## Running commands

```bash
# CLI help
docker compose run --rm peter --help

# Create a site
docker compose run --rm peter create-site --code ABC123 --name "Alpha Site"
```
