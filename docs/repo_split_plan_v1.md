# Repository Split Plan v1

This document records the current plan for how the prototype in `cognitio-core` should be split later.

## Why the current repo stays unified for now

At the current stage, keeping one repo is still useful because the following pieces are evolving together:

- `DocumentIR`
- PDF/text ingestion
- document runtime handles
- orchestrator / guided reading flow
- protocol events
- annotation sandbox

Splitting too early would slow down iteration because changes to one layer still frequently force changes to the others.

## Target future layout

The intended long-term layout is:

```text
cognitio-core
cognitio-frontend
```

Then, once the document layer is stable enough, split further into:

```text
cognitio-document
cognitio-core
cognitio-frontend
```

## Module responsibilities

### `cognitio-document`
This future repo should own the document-centric layer:

- source adapters (`pdf`, `text`, later `latex`)
- page extraction
- normalization into `DocumentIR`
- localized evidence
- document relations
- selector / locator / traversal helpers
- document runtime handles over finalized IR

Roughly speaking, `cognitio-document` is responsible for making a document:

- stable
- queryable
- selectable
- reusable by stronger models later

It should **not** own reading policy.

### `cognitio-core`
This repo should remain the runtime/intelligence layer:

- guided reading orchestrator
- planning
- highlights / warnings / advice
- annotation lifecycle
- research subtask flow
- sandbox and compilation loop
- model providers
- transport / service entrypoints

Roughly speaking, `cognitio-core` is responsible for deciding:

- what to read next
- what deserves attention
- when to annotate
- when to warn
- when to advise stopping or skipping

### `cognitio-frontend`
This future repo should own the user-facing application:

- reading UI
- annotation rendering
- highlight display
- advice / warning display
- user interventions during reading
- event stream consumption

## Recommended split order

### Phase 1: keep this repo as `cognitio-core`
Short term, continue using this repo as the unified prototype while stabilizing:

- `DocumentIR`
- document runtime API
- event protocol
- guided reading loop

### Phase 2: extract `cognitio-document`
When the following are stable enough, extract the document layer:

- `DocumentIR` schema is mostly stable
- localized evidence / relations stop changing every day
- document handle API has a clear minimum shape
- PDF/text/latex ingest boundaries are clearer

Likely directories to extract later:

```text
app/domain/document_ir.py
app/ingest/
app/runtime/document_handles.py
app/runtime/node_handle.py      # maybe split, depending on tool coupling
parts of app/runtime/tool_registry.py
relevant tests under tests/ingest/ and tests/runtime/
```

### Phase 3: keep `cognitio-core` focused on reading runtime
After extraction, `cognitio-core` should depend on the document package instead of owning the full parsing stack.

At that point, this repo should get cleaner boundaries around:

- orchestration
- model providers
- protocol / streaming
- sandboxed annotation workflow
- research tasks

## Practical migration strategy

Do **not** rewrite everything in one shot.

Recommended migration path:

1. First stabilize document-facing interfaces inside this repo.
2. Move document code into a more explicit internal boundary.
3. Extract to `cognitio-document` only after tests and imports are already clean.
4. Keep `cognitio-core` consuming the extracted package with minimal behavior change.

## Immediate next milestones inside this repo

Before extraction, the highest-value document work is:

1. improve selector ergonomics
   - `select_section`
   - `select_equation`
   - better figure/table lookup
2. strengthen relation traversal
   - captions
   - nearby explanatory paragraphs
   - evidence chains
3. make the document runtime easier for model tools to call
4. separate pure document logic from runtime policy logic more cleanly

## Naming note

Current repo name `cognitio-core` is acceptable because this repo currently contains more than the pure document layer.

If the split happens later, `cognitio-document` should become the stable document-perception layer, while `cognitio-core` remains the guided-reading runtime built on top of it.
