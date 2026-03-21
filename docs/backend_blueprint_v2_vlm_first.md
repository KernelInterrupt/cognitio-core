# Backend Blueprint v2: VLM-first Guided Reading Backend

This document replaces the earlier “parser-heavy” direction with a simpler backend strategy.

## 1. Positioning

Cognitio is a **guided reading engine**.

It is not:
- a chatbot
- a one-shot summarizer
- a generic document ETL toolkit

It should:
- guide user attention while reading
- move through a document incrementally
- attach selective annotations to concrete nodes
- emit warnings and advice when needed
- stay simple enough to evolve quickly

## 2. Architectural Decision

## Final choice

Use a **minimal ingestion backbone** plus a **VLM-first understanding layer**.

In short:
- keep traditional parsing as thin as possible
- avoid heavy local model stacks on the main path
- prefer a single capable VLM over a pile of layout/table/OCR submodels
- normalize everything into our own `DocumentIR`

This means:
- **Do not use full Docling as the main backend skeleton**
- **Do not depend on PyTorch/ONNX on the default path**
- **Do not build the system around a complicated parser pipeline**
- **Do use page images + optional text layer + VLM analysis**

## 3. Why this route

### 3.1 Product fit

Our job is not “perfect document conversion”.
Our job is “guided reading”.

For guided reading, the critical outputs are:
- reading order
- paragraph-like units
- heading boundaries
- figure/table anchors
- importance and warning signals
- annotation targets

A VLM can often produce these directly or with light normalization.

### 3.2 Engineering fit

A parser-heavy stack creates too much cost:
- Torch CPU is heavy
- ONNX deployment is often annoying
- different submodels mean more moving parts
- debugging conversion quality becomes difficult

A VLM-first stack keeps the core simpler:
- one main model path
- one main prompt family
- one IR normalization layer
- easier provider swapping (`llama.cpp`, `ollama`, remote OpenAI-compatible APIs)

### 3.3 License fit

This also helps us stay closer to an Apache-friendly architecture by avoiding unnecessary dependency spread.

## 4. Main system shape

```text
source document
  -> thin ingest
  -> page images + optional text layer
  -> VLM page/document analysis
  -> ParsedDocument
  -> DocumentIR
  -> planner
  -> guided reading orchestrator
  -> highlight / warning / advice / annotation / research
```

## 5. Ingestion philosophy

### 5.1 Thin ingest, not smart ingest

The ingest layer should only do cheap, reliable work:
- load bytes or text
- detect obvious source properties
- split plain text into paragraph blocks
- render PDF pages into images
- extract text layer when easily available
- preserve coordinates and provenance when available

The ingest layer should **not** try to be the main intelligence center.

### 5.2 Use text layer when present

If a PDF already contains usable text:
- keep it
- pass it to the VLM as auxiliary context
- use it to stabilize paragraph text and node IDs

### 5.3 Use page images as the universal fallback

Every PDF can always degrade to:
- page image(s)
- optional local text snippets
- VLM inference

This gives us one universal route for:
- papers
- manuals
- scanned instructions
- mixed-layout technical documents

## 6. Document pipeline

## Stage A: Source acquisition

Inputs:
- PDF
- LaTeX source
- plain text / markdown
- future: HTML or EPUB

Output:
- `DocumentSource`

## Stage B: Thin parse

Output:
- `ParsedDocument`

This is intentionally lightweight.

`ParsedDocument` should carry:
- metadata
- pages
- blocks
- text
- bbox when available
- image references when available
- provenance

## Stage C: VLM analysis

A VLM should be able to consume:
- page image
- extracted text layer for the page, if any
- user reading goal
- optional local document context

It should return structured results like:
- block segmentation
- reading order
- heading candidates
- figure/table/code/equation anchors
- suspicious instruction injection / hidden-content warnings
- page-level relevance to user goal

## Stage D: IR normalization

Normalize all upstream outputs into `DocumentIR`.

This is the stable contract for the rest of the system.

## 7. IR contract

The core runtime should only depend on `DocumentIR`, not on any parser-specific format.

`DocumentIR` should preserve:
- stable node IDs
- node kinds
- text content
- reading order
- parent/child structure
- provenance
- page number and bbox when known

## 8. Playwright-like reading API

This stays unchanged.

```python
node = select(node_id)
node.highlight(...)
node.warning(...)
node.advice(...)
node.open_annotation(...)
node.research(...)
```

This is important because the model should interact with the document as if it is navigating a structured reading surface.

## 9. Annotation sandbox

The annotation sandbox remains constrained:
- one virtual file per annotation
- canonical file name: `file.tex`
- locked preamble/template region
- editable body region only
- compile loop returns structured errors

The model should not be allowed to rewrite template-level `\usepackage` or document skeleton content.

## 10. Research subtask

`research()` remains an isolated capability.

It should:
- run as a sidecar task
- not derail the main reading loop
- return concise findings back into the run

This is architecturally separate from ordinary paragraph reading.

## 11. Recommended implementation order

### Phase 1
- introduce `DocumentSource`
- introduce thin ingest router
- introduce `ParsedDocument`
- support plain text immediately

### Phase 2
- add PDF page-image path
- add optional text-layer extraction
- define VLM structured output schema

### Phase 3
- implement `ParsedDocument -> DocumentIR` normalizer
- plug it into the existing orchestrator

### Phase 4
- implement a first VLM parser adapter
- support page-level block extraction and heading recovery

### Phase 5
- add interactive checkpoints and richer research flows

## 12. What we are explicitly not optimizing for right now

- perfect PDF reconstruction
- exact publisher-grade layout recovery
- exhaustive table semantics
- fully local torch-based model pipelines
- docling/full-pipeline compatibility as a hard requirement

## 13. Practical consequence

The product should behave like this:
- thin parsing provides enough substrate
- VLM performs the heavy semantic lift
- normalization turns model output into stable internal nodes
- guided reading runtime drives user attention

That is the intended backbone.
