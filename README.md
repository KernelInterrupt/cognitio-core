# Cognitio Core

Cognitio is a **guided reading backend** for papers, manuals, and other structured technical documents.

It is:
- **not** a chatbot
- **not** a one-shot summarizer
- **not** a generic RAG answer box

It is designed to:
- build a stable `DocumentIR` from source documents
- guide user attention during reading
- attach selective highlights and annotations to specific document nodes
- surface warnings and reading advice
- support a constrained annotation-editing sandbox

## Current status

This repository is currently the **core/backend** project. It contains:
- source ingestion (`text`, evolving `pdf`, future `latex`)
- `DocumentIR` and protocol models built on Pydantic
- a document runtime with playwright-like handles over finalized IR
- a guided reading orchestrator
- annotation sandbox primitives
- a headless CLI for observing event flow before frontend integration

## Architecture snapshot

```text
source document
  -> ingest / parse / normalize
  -> DocumentIR
  -> document runtime handles
  -> guided reading orchestrator
  -> events / highlights / annotations / advice / warnings
```

### Core layers

- `app/domain/`: IR models and domain objects
- `app/ingest/`: source -> parsed document -> normalized IR
- `app/runtime/`: orchestrator and document runtime handles
- `app/protocol/`: event / command schemas
- `app/sandbox/`: annotation workspace and fake compiler
- `app/adapters/`: LLM/VLM/source integrations

## Document runtime direction

The runtime already supports querying the finalized IR instead of reparsing PDFs repeatedly.
Examples:

```python
from app.runtime.tool_registry import ToolRegistry

registry = ToolRegistry(document_ir)
doc = registry.document()

page = doc.page(1)
paragraph = doc.select_paragraph("core idea")
figure = doc.select_figure("Figure 1")
nearby = doc.select_near_figure("Figure 1")
caption_nodes = doc.captions_of("evi_0002")
```

This is intended to grow into a more complete playwright-like document API.

## Planned repository split

This repo currently holds the backend/core prototype only; the frontend is planned as a separate repo.
The intended later layout is:

```text
cognitio-document
cognitio-core
cognitio-frontend
```

The current plan is documented in [`docs/repo_split_plan_v1.md`](docs/repo_split_plan_v1.md).

Long-horizon backend execution docs:
- [`docs/implementation_master_plan_v1.md`](docs/implementation_master_plan_v1.md)
- [`docs/execution_checklist_v1.md`](docs/execution_checklist_v1.md)
- [`docs/playwright_like_api_v1.md`](docs/playwright_like_api_v1.md)
- [`docs/sandbox_contract_v1.md`](docs/sandbox_contract_v1.md)

In short:
- `cognitio-document` will own document perception and runtime handles
- `cognitio-core` will own guided reading orchestration and backend/runtime policy
- `cognitio-frontend` will stay as a separate user-facing application repo

## Quickstart

### 1. Create environment

Using the local project conda/venv is fine; the project metadata is in `pyproject.toml`.

### 2. Install dependencies

```bash
pip install -r requirements.txt
pip install -e .[dev]
```

### 3. Run tests

```bash
pytest -q
/home/pc/cognitio/.conda/bin/ruff check app tests
```

### 4. Run the headless CLI

```bash
python -m app.cli.run_headless \
  --input /path/to/document.txt \
  --goal "读这篇论文" \
  --provider heuristic \
  --jsonl
```

Or probe Ollama connectivity:

```bash
python -m app.cli.run_headless probe-ollama --model qwen3:4b --jsonl
```

## License

Apache-2.0. See [LICENSE](./LICENSE).

## Design notes

More detailed design notes live in `docs/`, including:
- `docs/backend_blueprint_v1.md`
- `docs/backend_blueprint_v2_vlm_first.md`
- `docs/pdf_ir_backend_v1.md`
- `docs/ollama_integration_v1.md`
