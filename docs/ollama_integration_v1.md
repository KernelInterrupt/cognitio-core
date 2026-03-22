# Ollama Integration v1

## Position

Ollama is used in this project in **two different roles**, and they must not be confused.

### Role A: local document-ingest model service
This is the currently important local Ollama path.

Concrete example used in this project:
- `ibm/granite-docling:258m`

This is the local model path used for:
- PDF page -> doctag
- PDF -> IR groundwork
- local document perception experiments

### Role B: optional local LLM provider
This exists as an adapter path for planning / guided reading / annotation / research experiments, but it is **not** the recommended main backend-agent path.

The product direction remains:
- local lightweight model for `pdf -> IR`
- stronger cloud model (for example GPT / Gemini class models) for guided reading and annotation policy

So Ollama LLM support should be treated as:
- optional
- local fallback / debug path
- not the default recommended agent deployment

---

## Default endpoint behavior

The backend defaults to:

- `OLLAMA_BASE_URL=http://127.0.0.1:11434`

This matches Ollama's documented local API endpoint.

## Important constraint

Do **not** assume that a backend running inside WSL can always reach a Windows-hosted Ollama at `127.0.0.1:11434`.

Because of that, the product rule is:

- support explicit `OLLAMA_BASE_URL`
- provide connectivity probing
- avoid dangerous defaults such as broad external exposure
- avoid machine-specific hardcoded interface addresses as a product assumption

---

## Provider usage

### For local document ingest
The important model example is:

- `ibm/granite-docling:258m`

### For optional local LLM experiments
Use an **explicitly chosen** local model instead of relying on a baked-in tiny example.

Example:

`create_provider("ollama", model="<explicit-local-llm>")`

The model should be chosen deliberately by the operator.
It should not be interpreted as the recommended production guided-reading model.

Optional configuration:

- `OLLAMA_BASE_URL`
- `OLLAMA_LLM_MODEL`

---

## CLI preflight

The headless CLI performs an Ollama reachability + model-availability probe before a run starts when `--provider ollama` is selected.

It also exposes a direct probe command. A realistic example for current local ingest work is:

- `cognitio-headless probe-ollama --model ibm/granite-docling:258m`

This keeps connectivity failures and missing-model issues out of the main flow.

---

## Connectivity strategy

### Safe default
- try the configured `OLLAMA_BASE_URL`
- otherwise try the documented local default

### Not a default recommendation
- binding Ollama to `0.0.0.0`
- hardcoding one specific WSL virtual interface IP as a universal fix

---

## Current use in this project

### Actual local model path in active use
- `ibm/granite-docling:258m` for local PDF -> IR / doctag work

### Not the recommended main agent path
Ollama LLM support exists, but the intended main backend-agent path is still stronger remote models rather than tiny local LLMs.
