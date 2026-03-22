# Implementation Master Plan v1

## 0. How to use this document after context compression

When a future session resumes with reduced context, the agent should:

1. read this file first
2. then read `docs/execution_checklist_v1.md`
3. continue from the first unchecked task in the current focus area
4. after completing a task:
   - update the checklist
   - leave a short note if the implementation changed the plan
   - run validation
   - commit if the slice is coherent

This file is the **source of truth** for the long-horizon backend implementation of:

- the **document layer**
- the **agent sandbox layer**

Supporting technical specs that future sessions should also consult when relevant:

- `docs/playwright_like_api_v1.md`
- `docs/sandbox_contract_v1.md`

`cognitio-core` is a **backend repo only**.
The frontend stays in a separate repo and is **not** part of this execution plan.

---

## 1. Product goal

Build the backend core of Cognitio so that:

- source documents become stable `DocumentIR`
- the backend can navigate documents through a document-centric API rather than reparsing PDFs repeatedly
- annotation editing runs through a constrained sandbox with a locked template and an editable body region
- the sandbox can support different model styles:
  - tool-first models
  - read/write-oriented models
  - bash-oriented models as fallback only
- the resulting codebase is ready to later split the document layer into `cognitio-document`

---

## 2. Current baseline in the repo

### 2.1 Document layer baseline

Already implemented:

- `DocumentIR` with:
  - `nodes`
  - `localized_evidence`
  - `relations`
- normalized PDF ingest that preserves localized evidence and relations
- internal document boundary at:
  - `app/document/navigator.py`
- document runtime handles at:
  - `app/runtime/document_handles.py`
  - `app/runtime/node_handle.py`
- core tool runtime consumes document querying instead of owning all traversal logic

Relevant files now:

- `app/domain/document_ir.py`
- `app/ingest/normalizer.py`
- `app/document/navigator.py`
- `app/runtime/document_handles.py`
- `app/runtime/node_handle.py`
- `app/runtime/tool_registry.py`

### 2.2 Sandbox baseline

Already implemented:

- single-workspace model
- single virtual file: `file.tex`
- locked template markers + editable region markers
- editable-region read/write/patch API
- compile step through a compiler abstraction
- fake compiler returning structured compile errors
- annotation service loop with limited retry attempts

Relevant files now:

- `app/sandbox/templates.py`
- `app/sandbox/workspace.py`
- `app/sandbox/handle.py`
- `app/sandbox/compiler.py`
- `app/services/annotation_service.py`
- `app/domain/annotation.py`

### 2.3 Key design decisions already frozen

These decisions should be treated as fixed unless a later task explicitly changes them.

#### Document side

- the stable unit is `DocumentIR`, not raw PDF text
- `localized_evidence` is separate from primary reading nodes
- figure/table/equation relations belong in IR, not in ad hoc runtime memory
- document querying should move toward a future `cognitio-document` extraction boundary

#### Sandbox side

- **single virtual file** stays the primary interface
- the file remains `file.tex`
- models should use **structured tools first**
- bash is fallback only, not the primary interface
- the LaTeX template is **locked**
- models must not freely modify `\usepackage`, `\documentclass`, or template-owned macros
- annotation generation is an iterative **edit -> compile -> fix** workflow

---

## 3. Target architecture

## 3.1 Document architecture target

Target layering inside the current repo:

```text
app/domain/document_ir.py         # schema / stable IR objects
app/ingest/                       # source -> parsed -> normalized IR
app/document/                     # pure document querying/navigation/traversal
app/runtime/document_handles.py   # runtime-facing handles over document APIs
app/runtime/tool_registry.py      # core actions layered on top of document APIs
```

The rule is:

- `app/document/` answers structural questions about the document
- `app/runtime/` owns actions and policy

Examples of **document responsibilities**:

- find a paragraph on page 3
- find the first figure whose text contains `Figure 2`
- get captions for a figure
- get nearby explanatory paragraphs
- traverse evidence links

Examples of **core/runtime responsibilities**:

- highlight a node
- open an annotation
- emit warning/advice
- request research
- enforce permission tiers

## 3.2 Sandbox architecture target

Target layering inside the current repo:

```text
app/domain/annotation.py          # compile result / compile error / annotation state
app/sandbox/templates.py          # locked template + markers
app/sandbox/workspace.py          # file ownership + editable region mechanics
app/sandbox/compiler.py           # compiler abstraction(s)
app/sandbox/handle.py             # model-facing sandbox operations
app/services/annotation_service.py# orchestration of edit/compile/fix attempts
```

The rule is:

- `workspace` owns file integrity and region boundaries
- `compiler` owns compile semantics
- `handle` exposes model-facing operations
- `annotation_service` owns attempt loop and provider interaction

---

## 4. Detailed technical plan: document layer

# D1. Stabilize the pure document boundary

### Goal
Make `app/document/` the place where pure document-side logic lives.

### Current status
Partially done:
- `DocumentNavigator` exists
- `ToolRegistry` now delegates structural queries to it

### Remaining work

1. decide which logic still belongs in runtime handles vs document package
2. reduce document knowledge inside `NodeHandle` where practical
3. define which future files should move directly into `cognitio-document`
4. keep document querying testable without highlight/annotation/research logic

### Completion criteria

- document querying can be tested with no runtime actions involved
- future extraction candidates are explicitly documented
- `ToolRegistry` contains no low-level graph/index building logic

---

# D2. Selector ergonomics

### Goal
Expose higher-level document navigation so downstream agent logic does not hand-roll traversal.

### Required selector surface

Current:
- `select(...)`
- `select_first(...)`
- `select_paragraph(...)`
- `select_figure(...)`
- `select_near_figure(...)`

Still needed:
- `select_section(...)`
- `select_equation(...)`
- `select_table(...)`
- `select_heading(...)` or decide to fold into `select_section(...)`
- page-scoped variants where missing
- relation-aware selectors, e.g.:
  - `select_caption_for(...)`
  - `select_nearest_paragraph_for(...)`

### Implementation notes

- selectors should return handles, not raw dicts
- use page filtering when possible instead of global scans
- support `text_contains` consistently across node/evidence selectors
- do not overfit selector names to papers only; manuals/instructions should remain valid

### Completion criteria

- common document navigation tasks no longer require manually inspecting raw relation lists
- figure/table/equation lookup feels symmetrical
- tests exist for every public high-level selector

---

# D3. Relation traversal upgrades

### Goal
Make relation traversal expressive enough for reading guidance and later frontend support.

### Current baseline
Already present:
- caption lookup helper
- nearby paragraph lookup helper
- generic `relations_for(...)`

### Remaining work

1. reverse relation helpers
2. grouped relation helpers by semantic family
3. evidence-chain traversal helpers
4. APIs for relation filtering by:
   - relation kind
   - source kind
   - target kind
   - page scope when derivable
5. decide whether relation families should stay as string literals or get grouped wrappers

### Concrete helper targets

- `evidence_for(node_id)`
- `captions_of(item_id)`
- `nearby_paragraphs_of(item_id)`
- `incoming_relations_for(item_id)`
- `outgoing_relations_for(item_id)`
- `supporting_evidence_for(node_id)`
- `non_textual_evidence_for(node_id)`

### Completion criteria

- relation traversal is useful enough that downstream core logic rarely touches raw relation arrays directly
- tests cover forward and reverse traversal patterns

---

# D4. IR stabilization review

### Goal
Make the current `DocumentIR` closer to the extraction-ready format for `cognitio-document`.

### Review topics

1. metadata structure
   - is `page_count` enough?
   - do we need source/backend provenance fields in normalized metadata?
2. localized evidence structure
   - do we need spans?
   - do we need normalized evidence provenance shape instead of loose dicts?
3. relation structure
   - do we need typed wrappers later or is one relation model enough?
4. node/evidence ID stability
   - current IDs are runtime-generated and deterministic per normalization pass
   - decide how much stability is required across repeated ingests

### Constraints

- avoid premature overengineering
- preserve Pydantic simplicity
- do not introduce confidence floats or shaky probabilistic fields

### Completion criteria

- there is a clearly documented extraction-ready subset of `DocumentIR`
- no obvious document-shape concerns remain trapped in unrelated runtime code

---

# D5. Extraction readiness for future `cognitio-document`

### Goal
Prepare for future repo split without actually splitting now.

### Tasks

1. maintain `app/document/` as the internal destination for pure document logic
2. identify additional files that should later move there or into the future repo
3. reduce imports that point from document concerns back into runtime concerns
4. decide whether `NodeHandle` belongs to:
   - document
   - core
   - or a thin bridge layer

### Preliminary expectation

Very likely future extraction candidates:

- `app/domain/document_ir.py`
- `app/ingest/`
- `app/document/`
- `app/runtime/document_handles.py`
- maybe part of `app/runtime/node_handle.py`
- maybe part of `app/runtime/tool_registry.py`

### Completion criteria

- extracting `cognitio-document` later would be mostly file movement + import cleanup, not architectural surgery

---

## 5. Detailed technical plan: sandbox layer

# S1. Workspace lifecycle completion

### Goal
Make the annotation sandbox lifecycle explicit and complete.

### Current baseline
Already present:
- workspace initialization
- read full file
- read editable region
- write editable region
- patch editable region
- compile
- submit after successful compile

### Remaining work

1. define explicit state model for workspace/annotation editing:
   - initialized
   - editing
   - compile_failed
   - compiled
   - submitted
2. decide where state lives:
   - `Annotation`
   - `WorkspaceHandle`
   - or both with clear authority
3. track attempt count and last action more explicitly
4. expose stable status transitions to higher-level runtime/service code

### Completion criteria

- annotation editing is a well-defined finite workflow, not just a bundle of methods

---

# S2. Locked template protection hardening

### Goal
Ensure the model cannot freely mutate template-owned LaTeX regions.

### Current baseline
Already present:
- locked/editable markers
- editable region split by markers
- basic validation for missing `\usepackage`, `\documentclass`, `\end{document}`
- fake compiler rejects missing required markers

### Current weakness
The existing validation is still heuristic and too weak.
A model could potentially change template-owned content while leaving some required strings present.

### Required hardening direction

1. canonicalize the locked prefix and suffix at initialization time
2. compare current locked regions against canonical expected locked regions
3. reject any mutation outside the editable region, not only missing strings
4. keep the template owner responsible for:
   - `\documentclass`
   - `\usepackage`
   - macro declarations
   - document open/close structure
5. keep annotation-specific editable content restricted to the body region only

### Concrete implementation options

Preferred:
- `AnnotationWorkspace` stores expected locked prefix/suffix in memory or recomputes them from the template
- validation checks exact locked-region equality after normalizing line endings

Optional later:
- template version field
- per-template checksum/hashing for stronger validation

### Completion criteria

- any attempt to modify locked regions is surfaced as a structured error
- preamble corruption cannot silently pass validation

---

# S3. Compile protocol stabilization

### Goal
Make compile behavior machine-friendly for repeated model-driven repair loops.

### Current baseline
Already present:
- `CompileResult`
- `CompileError`
- fake compiler codes such as:
  - `LOCKED_REGION_MODIFICATION`
  - `COMPILE_VALIDATION_ERROR`

### Remaining work

1. stabilize error code taxonomy
2. ensure all sandbox validation failures map to structured compile errors
3. distinguish:
   - locked-region violations
   - template/schema violations
   - render/compile failures
4. decide minimal error shape to preserve:
   - `code`
   - `message`
   - `line`
   - `snippet`
5. keep repeated compile attempts deterministic

### Recommended error-code families

- `LOCKED_REGION_MODIFICATION`
- `TEMPLATE_STRUCTURE_ERROR`
- `ANNOTATION_SCHEMA_ERROR`
- `LATEX_COMPILE_ERROR`   # future real compiler path
- `SUBMISSION_PRECONDITION_ERROR`

### Completion criteria

- higher-level agent logic can branch on compile error code instead of parsing raw messages

---

# S4. Model-facing sandbox tool contract

### Goal
Define the exact tool contract exposed to providers/models.

### Frozen interface direction

The primary interface remains tool-oriented and centered on `file.tex`.

### Core operations

Required public operations:
- `read_file()`
- `read_body()`
- `write_body(content)`
- `patch_body(old, new)`
- `compile_annotation()`
- `get_compile_errors()`
- `submit_annotation()`

### Compatibility target

#### Tool-first models
Use direct structured operations.

#### Read/write-oriented models
Expose the body as editable file content with explicit locked-region rules.

#### Bash-oriented models
Allow fallback wrappers later, but keep them translated onto the same structured workspace contract.
The fallback must not bypass locked-region guarantees.

### Important rule

Even if bash fallback is introduced later, bash must not become a second unrestricted sandbox interface.
It must remain a compatibility layer over the same constrained operations.

### Completion criteria

- the tool surface is explicit enough that future provider adapters can target it consistently
- structured tools remain primary

---

# S5. Recovery loop readiness

### Goal
Support robust edit -> compile -> fix loops.

### Current baseline
Already present:
- `AnnotationService.render_annotation(...)`
- bounded retry loop with `max_attempts`
- compile errors passed back into the next provider request

### Remaining work

1. persist last compile result more explicitly
2. ensure compile errors are preserved across attempts in a stable shape
3. decide terminal stop conditions:
   - max attempts reached
   - repeated identical locked-region failure
   - provider emits submit without successful compile
4. support richer attempt diagnostics for debugging
5. make repeated failure states visible to orchestrator/protocol layer if needed

### Completion criteria

- multi-step repair loops can be tested deterministically
- repeated failure behavior is predictable

---

# S6. Real compiler migration path

### Goal
Keep the fake compiler now, but define a clean path to a real compiler later.

### Current baseline
- `FakeCompiler` is useful for workflow testing
- it does not yet represent real LaTeX failure modes

### Planned abstraction

Move toward something like:

```text
Compiler
  - FakeCompiler
  - LatexmkCompiler (future)
```

### Requirements for future real compiler adapter

- keep the same `CompileResult` / `CompileError` interface
- do not let the compiler mutate the locked template rules
- parse compiler stderr/log into structured errors where possible
- keep the rest of the sandbox unaware of compiler backend differences

### Completion criteria

- switching compiler backend should not require changing provider-facing tool semantics

---

# S7. Sandbox boundary cleanup

### Goal
Ensure sandbox internals stay independent of provider/orchestrator policy.

### Rules

- `workspace` should not know about model providers
- `compiler` should not know about orchestrator policy
- `handle` should remain a thin operational layer
- `annotation_service` should own retry orchestration
- provider-specific prompting belongs outside sandbox core

### Completion criteria

- sandbox can be tested without full orchestrator
- provider swaps do not require sandbox rewrites

---

## 6. Execution order

Recommended order from now on:

1. D2 selector ergonomics
2. D3 relation traversal upgrades
3. D4 IR stabilization review
4. D5 extraction readiness cleanup
5. S1 workspace lifecycle completion
6. S2 locked template protection hardening
7. S3 compile protocol stabilization
8. S4 model-facing sandbox tool contract
9. S5 recovery loop readiness
10. S6 real compiler migration path scaffolding
11. S7 sandbox boundary cleanup review

Reason:
- document side is already in motion and should be brought closer to extraction readiness first
- sandbox side already has a baseline and can then be completed on top of a more stable core

---

## 7. Done definition for this long task

This long task is complete when:

### Document side
- selector surface is materially richer and well tested
- relation traversal is ergonomic and stable
- `DocumentIR` shape has a documented stable subset
- future `cognitio-document` extraction path is technically clear

### Sandbox side
- workspace lifecycle is explicit
- locked template protection is robust against out-of-region edits
- compile protocol is stable and structured
- provider-facing tool contract is explicit
- iterative repair loop is deterministic and well tested

---

## 8. Resume instruction for future sessions

If a future session starts after heavy context compression, do exactly this:

1. read `docs/implementation_master_plan_v1.md`
2. read `docs/execution_checklist_v1.md`
3. start from the first unchecked item in D2 unless the user redirects
4. after each coherent slice:
   - update checkboxes
   - run validation
   - commit if appropriate
