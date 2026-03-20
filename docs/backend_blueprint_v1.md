# Backend Blueprint v1

This document condenses the current understanding of the project into an engineering outline that can be reused later.

## 0. Project Positioning

The system is a **guided reading runtime** for complex documents.

It is:

- not a chatbot
- not a one-shot summarizer
- not a generic RAG answer box

It should:

- guide user attention during reading
- process the document incrementally
- attach contextual annotations to specific nodes
- support warnings and reading advice
- work with papers, manuals, instructions, and similar structured documents

## 1. Frozen Decisions

1. The core abstraction is **Document IR**, not raw PDF/text.
2. Main flow is **light global planning + sequential guided reading**.
3. The system should support **goal-conditioned reading**.
4. The system should support **user interventions during reading**.
5. Tools are primary; **bash is fallback only**.
6. `warning` and `highlight` are distinct semantics.
7. No float confidence scores in core schemas.
8. Backend validation comes before frontend polish.
9. Project licensing target is **Apache-2.0**, so avoid GPL/AGPL contagion.

## 2. Product-Level Mental Model

### Core loop

1. ingest source
2. build `DocumentIR`
3. infer internal `reading_mode`
4. create a lightweight reading plan
5. read nodes sequentially
6. decide attention level
7. optionally annotate
8. optionally raise warning
9. occasionally generate advice
10. accept user interventions at checkpoints

### Supported source examples

- research papers
- device manuals
- installation instructions
- technical specs
- long-form tutorials

## 3. Backend Modules

### 3.1 Source Adapters

Convert source documents into `DocumentIR`.

Planned adapters:

- `text -> DocumentIR` (MVP)
- `pdf -> DocumentIR` (later)
- `latex -> DocumentIR` (later)

### 3.2 Planner

Consumes full `DocumentIR` and user goal, then produces:

- inferred `reading_mode`
- section/node priorities
- likely key nodes
- skip hints
- annotation budget hints

### 3.3 Guided Reading Runtime

Consumes:

- `DocumentIR`
- reading plan
- current user goal
- intervention queue

Produces:

- progress events
- highlights
- annotations
- warnings
- advice

### 3.4 Annotation Workspace

A constrained editing environment for annotation generation.

Principles:

- one workspace per annotation
- one virtual file: `file.tex`
- structured tools first
- compile loop with structured errors

### 3.5 Research

`research()` exists conceptually, but is not part of MVP critical path.

It is an auxiliary, isolated capability and must not replace the main reading process.

### 3.6 Protocol

The system should expose a command/event protocol rather than a chat transcript protocol.

### 3.7 CLI Observer

Before frontend integration, the backend should be observable from the terminal:

- event stream
- current node
- applied highlights
- warnings
- annotation lifecycle
- final advice

## 4. MVP Scope

### In scope

- `text -> DocumentIR`
- one LLM integration
- planning pass
- sequential reading pass
- user interventions at checkpoints
- `highlight`
- `warning`
- `advice`
- annotation workspace with fake compiler
- headless CLI demo

### Out of scope for first cut

- Flutter UI
- full PDF parsing
- LaTeX parsing
- research subagents
- Dockerized sandbox
- multi-model adapters
- production database design

## 5. Suggested Directory Shape

```text
backend/
  app/
    domain/
      document_ir.py
      reading_goal.py
      signals.py
      annotation.py
      reading_run.py
    runtime/
      planner.py
      orchestrator.py
      tool_registry.py
      intervention_queue.py
    adapters/
      source/
        text_adapter.py
      llm/
        base.py
        openai_adapter.py
    sandbox/
      workspace.py
      compiler.py
      templates.py
    protocol/
      commands.py
      events.py
    cli/
      run_headless.py
```

## 6. Document IR Schema v1

Use a DOM-like IR rather than a compiler-style AST.

### Top-level object

```python
class DocumentIR(BaseModel):
    document_id: str
    root_id: str
    metadata: DocumentMetadata
    nodes: dict[str, IRNode]
    reading_order: list[str]
    created_at: str
    ir_version: str = "1.0"
```

### Metadata

```python
class DocumentMetadata(BaseModel):
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    source_kind: Literal["text", "pdf", "latex"]
    language: str | None = None
```

### Base node

```python
class BaseNode(BaseModel):
    id: str
    kind: Literal["document", "section", "paragraph", "equation", "figure", "table"]
    parent_id: str | None = None
    children: list[str] = Field(default_factory=list)
    order_index: int
    provenance: Provenance | None = None
```

### Concrete nodes

```python
class DocumentNode(BaseNode):
    kind: Literal["document"] = "document"
    title: str | None = None

class SectionNode(BaseNode):
    kind: Literal["section"] = "section"
    title: str
    level: int

class ParagraphNode(BaseNode):
    kind: Literal["paragraph"] = "paragraph"
    text: str
    spans: list[TextSpan] = Field(default_factory=list)

class EquationNode(BaseNode):
    kind: Literal["equation"] = "equation"
    latex: str | None = None
    text_repr: str | None = None

class FigureNode(BaseNode):
    kind: Literal["figure"] = "figure"
    caption: str | None = None

class TableNode(BaseNode):
    kind: Literal["table"] = "table"
    caption: str | None = None
```

### Text spans

```python
class TextSpan(BaseModel):
    start: int
    end: int
    type: Literal["plain", "emphasis", "math", "citation_ref", "term"]
    text: str
```

### Provenance

```python
class Provenance(BaseModel):
    source_kind: Literal["text", "pdf", "latex"]
    pdf_page: int | None = None
    pdf_bbox: tuple[float, float, float, float] | None = None
    latex_file: str | None = None
    latex_line_start: int | None = None
    latex_line_end: int | None = None
```

### Runtime-attached state (stored separately from IR)

```python
HighlightLevel = Literal["skip", "normal", "important", "critical"]

class HighlightState(BaseModel):
    node_id: str
    level: HighlightLevel
    reason: str | None = None

class WarningSignal(BaseModel):
    warning_id: str
    target_node_id: str
    kind: Literal[
        "prompt_injection",
        "hidden_text",
        "instruction_like_content",
        "unsupported_claim",
        "weak_evidence",
        "overclaim",
        "evaluation_risk",
    ]
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    evidence: list[str] = Field(default_factory=list)

class Advice(BaseModel):
    advice_id: str
    scope: Literal["node", "section", "document", "run"]
    target_id: str
    kind: Literal[
        "continue_reading",
        "read_selectively",
        "skip_section",
        "revisit_node",
        "stop_reading",
        "validate_externally",
    ]
    message: str
    basis: list[str] = Field(default_factory=list)
```

### Goal and intervention

```python
class ReadingGoal(BaseModel):
    user_query: str
    constraints: list[str] = Field(default_factory=list)
    target_domain: str | None = None

class UserIntervention(BaseModel):
    intervention_id: str
    run_id: str
    kind: Literal[
        "clarify_goal",
        "change_priority",
        "ask_question",
        "request_skip",
        "focus_node",
        "request_pause",
    ]
    message: str
```

## 7. Runtime State Machine v1

The runtime is checkpoint-driven and sequential by default.

### High-level states

```text
idle
  -> ingesting
  -> planning
  -> ready
  -> reading_node
  -> deciding_attention
  -> maybe_warning
  -> maybe_annotating
  -> checkpoint
  -> next_node
  -> section_boundary
  -> maybe_advice
  -> completed
```

### Detailed behavior

#### `ingesting`

- parse input source
- build `DocumentIR`
- emit `document.ingested`

#### `planning`

- run lightweight full-document planning
- infer internal `reading_mode`
- generate reading plan
- emit `reading_mode.inferred`
- emit `reading_plan.created`

#### `reading_node`

- select next node from `reading_order`
- gather local context
- emit `reading.progress`

#### `deciding_attention`

- decide whether node is `skip|normal|important|critical`
- emit `highlight.applied`

#### `maybe_warning`

- inspect for security/reliability hazards
- emit `warning.raised` if needed

#### `maybe_annotating`

- create annotation only if worth it
- open workspace
- edit `file.tex`
- compile
- emit annotation lifecycle events

#### `checkpoint`

- poll user interventions
- if present, update run context / goal / local priority
- emit `run.awaiting_user_input` when pausing for input

#### `section_boundary`

- optional local advice
- revise section budget if needed

#### `maybe_advice`

- near end of section or run
- produce reading advice, not a generic summary

#### `completed`

- emit final advice if needed
- emit `run.completed`

### Invariants

1. Reading remains sequential unless explicitly redirected.
2. Annotation is selective, not exhaustive.
3. Warnings do not replace highlights.
4. User input is consumed only at checkpoints.
5. The runtime may use global plan context, but should not collapse into a one-shot summarizer.

## 8. Headless CLI Demo I/O Format

The CLI is the first observation surface for backend behavior.

### Example invocation

```bash
python -m app.cli.run_headless \
  --input ./examples/demo.txt \
  --goal "Read this paper and tell me whether its method can transfer to medical imaging" \
  --language zh
```

### Input expectations

#### Source file

- plain text for MVP
- paragraphs separated by blank lines
- optional markdown-like section headers can be heuristically recognized

#### Goal

- required free-form user goal string

#### Optional interventions file

Can be appended later as line-delimited JSON events:

```json
{"at_node":"p_3","kind":"change_priority","message":"Focus on practical migration constraints, not theory."}
{"at_node":"p_7","kind":"ask_question","message":"Why is this assumption necessary?"}
```

### CLI output modes

#### Human-readable stream

```text
[document.ingested] document_id=doc_001 node_count=24
[reading_mode.inferred] value=paper_like source=inferred
[reading_plan.created] key_nodes=p_5,p_9,p_14
[run.started] run_id=run_001
[reading.progress] node_id=p_1 stage=reading
[highlight.applied] node_id=p_1 level=normal
[reading.progress] node_id=p_2 stage=reading
[highlight.applied] node_id=p_2 level=critical reason="core problem statement"
[annotation.opened] annotation_id=ann_001 target_node_id=p_2 type=intuition
[annotation.compiled] annotation_id=ann_001
[warning.raised] node_id=p_8 kind=instruction_like_content severity=high
[run.awaiting_user_input] node_id=p_8
[advice.generated] scope=section target_id=sec_2 kind=read_selectively
[run.completed] run_id=run_001
```

#### JSON Lines mode

Each line is one event:

```json
{"type":"document.ingested","payload":{"document_id":"doc_001","node_count":24}}
{"type":"reading_mode.inferred","payload":{"value":"paper_like","source":"inferred"}}
{"type":"reading.progress","payload":{"run_id":"run_001","node_id":"p_1","stage":"reading"}}
{"type":"highlight.applied","payload":{"node_id":"p_1","level":"normal","reason":null}}
```

### MVP event set

- `document.ingested`
- `reading_mode.inferred`
- `reading_plan.created`
- `run.started`
- `reading.progress`
- `highlight.applied`
- `warning.raised`
- `annotation.opened`
- `annotation.compile_failed`
- `annotation.compiled`
- `advice.generated`
- `run.awaiting_user_input`
- `run.completed`

## 9. Immediate Implementation Order

1. `document_ir.py`
2. `reading_goal.py`
3. `signals.py`
4. `text_adapter.py`
5. `planner.py`
6. `tool_registry.py`
7. `orchestrator.py`
8. `workspace.py`
9. `compiler.py`
10. `run_headless.py`

## 10. Success Criteria for MVP

1. The model performs a planning pass before sequential reading.
2. Highlights are sparse and useful.
3. Annotation is selective.
4. Warnings can flag obviously suspicious content.
5. Advice is actionable rather than summary-like.
6. User interventions change later reading behavior.
