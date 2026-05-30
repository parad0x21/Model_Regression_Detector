# Model Regression Detection System (MRDS)

> **An AI evaluation platform and deployment-safety system** — not an email-classification app. It continuously tests LLM-powered features against versioned golden datasets, detects regressions against promoted baselines, reports results, alerts Slack, and **blocks deployments when quality degrades**. The Customer Support Email Classifier is only the *first* feature under test.

📐 Design: [docs/architecture.md](docs/architecture.md) &nbsp;•&nbsp; 🗺️ Build plan: [docs/roadmap.md](docs/roadmap.md) &nbsp;•&nbsp; 🤖 Agent context: [CLAUDE.md](CLAUDE.md)

---

## Status

🚧 **Sprint 1 — Project Foundation.** The packaging, configuration, logging, and
CLI scaffolding are in place. Feature, evaluation, regression, reporting, Slack,
dashboard, CI, and Docker layers are implemented in later sprints (see the roadmap).

## Requirements

- Python 3.11+

## Quickstart

```bash
# 1. Create a virtual environment
python3.11 -m venv .venv && source .venv/bin/activate

# 2. Install the package (editable) with dev tooling
pip install -e ".[dev]"

# 3. (Optional) configure environment
cp .env.example .env   # fill in secrets later, when features need them

# 4. Run the CLI
mrds --help
mrds --version

# 5. Lint and test
ruff check .
ruff format --check .
pytest
```

The planned CLI commands (`evaluate`, `compare`, `report`, `promote-baseline`)
are registered but report "not implemented yet" until their sprints land.

## Configuration

Configuration is layered (lowest to highest precedence):

1. Built-in defaults (`src/mrds/config/settings.py`)
2. `config/settings.yaml` (committed, non-secret)
3. Environment variables / `.env` (secrets and per-environment overrides)

Secrets (`OPENAI_API_KEY`, `SLACK_WEBHOOK_URL`) come from the environment only and
are never committed. All other settings use the `MRDS_` prefix (e.g. `MRDS_LOG_LEVEL`).

## Project layout

See [docs/architecture.md](docs/architecture.md) for the full repository structure
and module responsibilities.
