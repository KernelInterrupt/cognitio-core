# Playwright-like API Spec v1

This document defines the intended **playwright-like API style** for Cognitio's backend document runtime.

The goal is not to imitate Playwright literally. The goal is to borrow the useful parts of its ergonomics:

- stable handles instead of loose data blobs
- explicit object hierarchy
- clear distinction between query operations and action operations
- chaining around document/page/node/evidence scopes
- operations that are easy for models to call repeatedly

This document is part of the long-horizon implementation plan and should be read together with:

- `docs/implementation_master_plan_v1.md`
- `docs/execution_checklist_v1.md`

---

## 1. Design intent

A generic agent reading raw PDFs usually has to repeatedly:

- split page text into blocks
- guess reading order
- find figures/captions manually
- reconstruct paragraph/evidence relationships

Cognitio should avoid this by giving the runtime a stable document object model.

So the backend should feel like:

```python
doc = registry.document()
page = doc.page(3)
para = doc.select_paragraph("core idea")
fig = doc.select_figure("Figure 2")
caption = fig.caption_nodes()
nearby = fig.nearby_paragraphs()
para.highlight("important")
ann = para.open_annotation("intuition")
```

That is the sense in which the API is **playwright-like**.

---

## 2. Object model

The intended runtime hierarchy is:

```text
DocumentHandle
  -> PageHandle
  -> NodeHandle
  -> LocalizedEvidenceHandle
  -> Annotation workspace handle (opened from a node)
```

### 2.1 `DocumentHandle`
Top-level entry point for querying a finalized `DocumentIR`.

Responsibilities:
- page access
- top-level selection
- global relation traversal helpers
- global evidence lookup

Should not directly own:
- compile loop logic
- model provider logic
- permission policy

### 2.2 `PageHandle`
Page-scoped view over the document.

Responsibilities:
- page-local node selection
- page-local evidence selection
- convenience methods for page subsets

### 2.3 `NodeHandle`
Stable handle around one IR node.

Responsibilities:
- inspect node kind/page/text
- traverse linked evidence/relations
- invoke core actions such as highlight / warning / annotation / research

### 2.4 `LocalizedEvidenceHandle`
Stable handle around one evidence object.

Responsibilities:
- inspect evidence kind/text/page
- traverse caption/nearby/relation links

### 2.5 Workspace / annotation handle
Opened from a node action such as `open_annotation(...)`.

Responsibilities:
- read and edit `file.tex`
- compile
- inspect compile errors
- submit on success

---

## 3. Query API vs action API

This distinction is mandatory.

## 3.1 Query API
These do not change runtime state.

Examples:
- `doc.page(1)`
- `doc.select_paragraph(...)`
- `page.figures()`
- `node.localized_evidence()`
- `figure.caption_nodes()`
- `doc.relations_for(...)`

These should be:
- deterministic
- easy to test
- document-side where possible

## 3.2 Action API
These do change runtime state or initiate workflows.

Examples:
- `node.highlight(...)`
- `node.warning(...)`
- `node.advice(...)`
- `node.open_annotation(...)`
- `node.research(...)`

These should stay in core/runtime territory, not in pure document navigation.

---

## 4. Required API surface

## 4.1 Document-level API

Already present or intended:

```python
doc.page(page_no)
doc.pages()
doc.select(node_id)
doc.select_first(...)
doc.select_paragraph(...)
doc.select_figure(...)
doc.select_near_figure(...)
doc.figures(...)
doc.evidence_for(node_id)
doc.captions_of(target_id)
doc.nearby_paragraphs_of(target_id)
doc.relations_for(target_id, kind=None)
```

Still intended:

```python
doc.select_section(...)
doc.select_table(...)
doc.select_equation(...)
doc.select_heading(...)   # optional if folded into section selection
```

## 4.2 Page-level API

Current / intended:

```python
page.nodes(kind=None)
page.paragraphs()
page.sections()
page.localized_evidence(kind=None)
page.figures()
page.select_paragraph(...)
page.select_figure(...)
```

Still intended later:

```python
page.tables()
page.equations()
page.select_table(...)
page.select_equation(...)
```

## 4.3 Node-level API

Current / intended:

```python
node.kind
node.page_no
node.text_content()
node.localized_evidence(kind=None)
node.relations(kind=None)
node.highlight(level, reason=None)
node.warning(...)
node.advice(...)
node.open_annotation(annotation_type, language="zh")
node.research(goal, scope=None)
```

## 4.4 Evidence-level API

Current / intended:

```python
evidence.kind
evidence.text
evidence.page_no
evidence.relations(kind=None)
evidence.caption_nodes()
evidence.nearby_paragraphs()
```

---

## 5. Return-type rules

### 5.1 Selection methods should prefer handles

For example:
- `select_paragraph(...) -> NodeHandle | None`
- `select_figure(...) -> LocalizedEvidenceHandle | None`

Do not return raw dicts or Pydantic models from the public runtime API unless there is a strong reason.

### 5.2 Bulk methods return lists of handles

For example:
- `page.paragraphs() -> list[NodeHandle]`
- `page.figures() -> list[LocalizedEvidenceHandle]`

### 5.3 Relation inspection may still return relation models

This is acceptable because relations are metadata objects rather than interactive handles.

---

## 6. Naming rules

### Use selection verbs for discovery
- `select_*`
- `page(...)`
- `figures()`
- `relations_for(...)`

### Use action verbs for side effects
- `highlight(...)`
- `warning(...)`
- `advice(...)`
- `open_annotation(...)`
- `research(...)`

### Keep names document-general
Avoid paper-only naming where possible.
The API should still work for manuals, installation instructions, and technical docs.

---

## 7. Boundary rules

### Pure document layer
Should own:
- structural selection
- page grouping
- relation traversal
- evidence traversal

### Core/runtime layer
Should own:
- highlight
- annotation
- advice
- warning
- research
- permission checks
- event emission

### Sandbox layer
Should own:
- opened annotation editing workflow
- `file.tex` constraints
- compile loop primitives

---

## 8. Sandbox fit with playwright-like style

The sandbox should also feel handle-based.

Example:

```python
annotation = node.open_annotation("intuition")
workspace = annotation.workspace()   # future shape, if introduced
workspace.read_body()
workspace.write_body("...")
result = workspace.compile_annotation()
errors = workspace.get_compile_errors()
workspace.submit_annotation()
```

Even if the current implementation returns different intermediate objects internally, the **public mental model** should stay handle-based.

---

## 9. Compatibility target for different model styles

### Tool-first models
Preferred path:
- explicit selection and workspace tools
- minimal ambiguity

### Read/write-oriented models
Expose body/file operations through structured wrappers.

### Bash-oriented models
Allowed only as fallback.
Any bash fallback must map onto the same constrained workspace model and must not bypass locked-region rules.

---

## 10. Immediate implementation implications

The next implementation slices should treat this API spec as the target.

Highest-priority missing pieces:

1. `select_section(...)`
2. `select_table(...)`
3. `select_equation(...)`
4. more relation-aware selectors
5. clearer workspace-handle story for annotation editing

