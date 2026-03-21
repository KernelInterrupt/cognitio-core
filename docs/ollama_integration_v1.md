# Ollama Integration v1

## Position

Ollama is treated as a **native local model service** option for guided reading.

It is not assumed to run in Docker.
Docker remains optional.

## Default behavior

The backend defaults to:

- `OLLAMA_BASE_URL=http://127.0.0.1:11434`

This matches Ollama's documented default local API endpoint.

## Important constraint

Do **not** assume that a backend running inside WSL can always reach a Windows-hosted Ollama at `127.0.0.1:11434`.

Some machines will work.
Some will not.

Because of that, the product rule is:

- support explicit `OLLAMA_BASE_URL`
- provide connectivity probing
- avoid dangerous defaults such as recommending broad external exposure
- avoid machine-specific hardcoded interface addresses as a product assumption

## Provider usage

`create_provider("ollama", model="qwen3:4b")`

Optional configuration:

- `OLLAMA_BASE_URL`

## Connectivity strategy

### Safe default
- try the configured `OLLAMA_BASE_URL`
- otherwise try the documented local default

### Not a default recommendation
- binding Ollama to `0.0.0.0`
- hardcoding one specific WSL virtual interface IP as a universal fix

## Current use in this project

The current `OllamaProvider` is intended for:
- planning
- guided reading
- annotation editing
- research subtasks

It is not yet the primary PDF -> IR provider.
