---
name: deep-researcher-agent
description: Use NVIDIA AI-Q Blueprint Deep Researcher Agent for research workflows, report generation, and source-backed answers.
license: Apache-2.0
metadata:
  author: NVIDIA
  tags:
    - ai-q
    - deep-research
    - research
    - nemo-agent-toolkit
---

# NVIDIA AI-Q Deep Researcher Agent Integration

Use this skill when a coding agent needs the NVIDIA AI-Q Deep Researcher Agent for research workflows, report generation, and source-backed answers.

## Project Overview

AI-Q is an NVIDIA AI Blueprint: an enterprise research agent built on the **NeMo Agent Toolkit (NAT)**. The deployed product is a research blueprint, not a general skill runtime. Agent behavior is driven by workflow YAML, Jinja2 prompts, and a data-source registry.

Primary boundaries:

- Backend Python package: `src/aiq_agent/`
- Data-source and tool packages: `sources/` (each is its own package)
- Configs, deployment, docs: `configs/`, `deploy/`, `docs/`

## Repository Structure

| Path | Purpose |
| :-- | :-- |
| `src/aiq_agent/` | Backend agent, FastAPI extensions, auth, observability, knowledge |
| `sources/` | Data-source / tool packages (e.g. `tavily_web_search`, `google_scholar_paper_search`) |
| `configs/` | Workflow YAML configs (e.g. `config_cli_default.yml`) |
| `frontends/ui/` | Next.js / React / TypeScript / Tailwind / KUI web UI |
| `frontends/benchmarks/` | Eval harnesses: `freshqa`, `deepsearch_qa`, `deepresearch_bench` |
| `mcp/` | Independent MCP server uv project, lockfile, tests, and release assets |
| `deploy/` | Docker Compose and Helm/Kubernetes assets; `deploy/.env` for secrets |
| `skills/` | API-consumer Agent Skills (`aiq-deploy`, `aiq-research`) |

## Build, Test, and Validation Commands

Python (run from the repo root; the project uses `uv`):

```bash
./scripts/setup.sh                    # one-time environment setup
uv sync --group dev                   # root AI-Q development environment
uv run ruff check .                   # lint
uv run ruff format --check .          # format check
uv run pytest                         # root and source-package tests
uv sync --project mcp --extra dev     # isolated MCP development environment
uv run --project mcp --extra dev pytest mcp/tests
```

Run the backend locally:

```bash
./scripts/start_cli.sh             # CLI mode (configs/config_cli_default.yml)
nat serve --config_file configs/config_cli_default.yml --port 8000
```

The backend API serves at `http://localhost:8000`.

## Ways to Run the Agents

### Command-line interface (CLI)

The CLI provides an interactive research assistant in your terminal:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run with the convenience script
./scripts/start_cli.sh

# Verbose logging
./scripts/start_cli.sh --verbose

# Or run directly with the NeMo Agent Toolkit CLI (dotenv loads deploy/.env into the environment)
dotenv -f deploy/.env run nat run --config_file configs/config_cli_default.yml --input "How do I install CUDA?"
```

### Web UI

For a full web-based experience:

```bash
./scripts/start_e2e.sh
```

This starts:
- Backend API server at `http://localhost:8000`
- Frontend UI at `http://localhost:3000`

### Async Deep Research Jobs

For public endpoints, SSE replay, report follow-up, and durable artifact access, refer to the [REST API documentation].

### MCP Server

Expose AI-Q to MCP clients through the standalone, stateless Streamable HTTP server:

```bash
: "${NVIDIA_API_KEY:?Set NVIDIA_API_KEY}"
: "${TAVILY_API_KEY:?Set TAVILY_API_KEY}"
uv sync --project mcp --extra dev
AIQ_CHECKPOINT_DB=postgresql://localhost/aiq_jobs \
  uv run --project mcp --extra dev aiq-mcp-server
```

The endpoint defaults to `http://localhost:9001/mcp` and advertises exactly `submit_query`, `poll_query`, and `get_final_report`.

## Configuration Files

The `configs/` directory holds YAML workflow configs that define agents, tools, LLMs, and routing. Use the one that matches your run mode and data sources:

| Config | Models | Description |
|--------|--------|-------------|
| `config_cli_default.yml` | Nemotron 3.5 Lightning; Nemotron 3 Ultra | CLI chat pipeline with Tavily and clarification; no knowledge backend. Paper search is a commented opt-in. |
| `config_web_default_llamaindex.yml` | Nemotron 3.5 Lightning; Nemotron 3 Ultra; Gemma 4 summary | Default web/API chat pipeline with LlamaIndex/ChromaDB and Tavily. Paper search is commented out. |
| `config_web_frag.yml` | Nemotron 3.5 Lightning; Nemotron 3 Ultra | Web/API and Helm base with Foundational RAG plus Tavily. Requires separately deployed RAG query and ingestion services. |
| `config_web_default_guardrails.yml` | Nemotron 3.5 Lightning; Nemotron 3 Ultra; Gemma 4 summary | LlamaIndex profile with workflow Guardrails explicitly attached. |

## Available Benchmarks

| Benchmark | Description | Location |
|-----------|-------------|----------|
| Deep Research Bench | RACE and FACT evaluation for research quality | `frontends/benchmarks/deepresearch_bench/` |
| FreshQA | Factuality evaluation on time-sensitive questions | `frontends/benchmarks/freshqa/` |

## Running Evaluations

```bash
dotenv -f deploy/.env run nat eval \
  --config_file frontends/benchmarks/deepresearch_bench/configs/config_deep_research_bench.yml
```

## Security and Auth Rules

- Never commit secrets, tokens, or environment-specific hostnames. Use environment variables and `SecretStr`; resolve API keys at runtime.
- Never print or log secret values, including in tool output or error messages.
- Missing-secret paths must degrade gracefully (stub/skip), not crash or leak.
- Respect authenticated data sources: honor `requires_auth`, per-user token pass-through, and backend token validators. Apply owner guardrails before loading protected report or artifact context into an agent.
- Do not weaken or bypass `AuthMiddleware`, validators, or auth gating without a prior design discussion.

## Skill Usage

- Repository-global rules live in the parent `AGENTS.md`.
- Task-specific runbooks live in `.agents/skills/` — load the relevant skill before starting a workflow it covers.
- API-consumer skills for calling a running AI-Q server live in `skills/` (`aiq-research`, `aiq-deploy`); they are a different audience and are not maintainer skills.
- These skills are guidance for coding agents working in this repository. They are not an in-product skill runtime and are not executed by the deployed AI-Q application.