---
name: cosmos-dataset-search
description: Use Cosmos Dataset Search for dataset discovery, search, and ingestion workflows.
license: Apache-2.0
metadata:
  author: NVIDIA
  tags:
    - cosmos
    - dataset-search
    - data-ingestion
    - rrag
---

# NVIDIA Cosmos Dataset Search Integration

Use this skill when a coding agent needs Cosmos Dataset Search for dataset discovery, search, and ingestion workflows.

## Project Overview

Cosmos Dataset Search is an NVIDIA blueprint for searching and discovering datasets across the NVIDIA ecosystem. It provides capabilities for finding datasets, embedding models, and managing data ingestion pipelines for research and development workflows.

## Repository Structure

The Cosmos Dataset Search repository contains:

- `src/` - Core source code for dataset search and ingestion
- `deploy/` - Deployment assets (Docker Compose, Helm charts)
- `docs/` - Documentation for API, deployment, and usage
- `deploy/standalone/` - Standalone deployment with MinIO, Milvus, and other services
- `scripts/` - Evaluation and performance scripts

## Key Components

### Dataset Search API

The dataset search service provides endpoints for:
- Searching datasets by topic, category, or metadata
- Filtering by source, format, and domain
- Paginated results with metadata enrichment

### Ingestion Pipeline

Manages data ingestion from various sources:
- Web crawling and dataset discovery
- Metadata extraction and normalization
- Storage in vector databases (Milvus, etc.)
- Quality validation and indexing

### Model Embedding

Supports embedding models for:
- Text embedding for semantic search
- Multi-modal embeddings (image, video)
- Integration with RAG (Retrieval-Augmented Generation) pipelines

## Usage Patterns

### Searching Datasets

Use the dataset search API to find relevant datasets for your use case:

```python
# Example: Search for GPU-accelerated data science datasets
results = dataset_search.search(
    query="GPU data science",
    filters={"domain": "machine-learning", "format": "parquet"}
)
```

### Ingesting Datasets

Set up ingestion pipelines for automated dataset collection:

```python
# Example: Start ingestion pipeline for web-sourced datasets
ingestion_job = ingestion_pipeline.start(
    source="web",
    query="machine learning datasets",
    target_storage="minio://datasets"
)
```

### Integration with RAG

Cosmos Dataset Search integrates with NVIDIA RAG blueprint for:
- Semantic search over discovered datasets
- Context retrieval for research questions
- Dataset metadata enrichment for LLM prompts

## Deployment

### Standalone Deployment

```bash
# Using Docker Compose
cd cosmos-dataset-search-main/deploy/standalone
docker compose up -d

# Or using Helm
helm install cosmos ./helm/mosaic-stack \
  -n cosmos --create-namespace
```

### Configuration

Set environment variables in `deploy/.env`:

```
COSMOS_DATASET_SEARCH_API_KEY=your-api-key
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MILVUS_URI=http://localhost:19530
```

## Skill Usage

- Repository-global rules live in the parent `AGENTS.md`.
- Task-specific runbooks live in `.agents/skills/` — load the relevant skill before starting a workflow it covers.
- These skills are guidance for coding agents working in this repository. They are not an in-product skill runtime.
- For integration with NeMo Agent Toolkit, configure data sources in `configs/` and register them in the `data_source_registry`.