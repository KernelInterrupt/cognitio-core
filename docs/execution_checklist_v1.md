# Execution Checklist v1

This file is the live execution tracker for the long task.

Rules:
- mark finished items with `[x]`
- mark unfinished items with `[ ]`
- keep notes short and factual
- after context compression, resume from the first meaningful unchecked item unless the user redirects

`cognitio-core` is backend-only.
Frontend work is tracked elsewhere and should not be folded into this checklist.

---

## Current priority order

1. finish the document layer to extraction-ready shape
2. finish the agent sandbox to stable tool-first shape
3. only then widen back out to larger core/runtime tasks

---

# D. Document layer

## D1. Internal document boundary cleanup
- [x] preserve localized evidence in final `DocumentIR`
- [x] preserve relations in final `DocumentIR`
- [x] create `app/document/` as an internal document-side boundary
- [x] add a pure `DocumentNavigator`
- [x] reduce traversal/index-building logic inside `ToolRegistry`
- [ ] decide whether `NodeHandle` should later live in document, core, or a bridge layer
- [ ] document the exact future extraction set for `cognitio-document`

Notes:
- first-round internal boundary cleanup is done
- `ToolRegistry` now layers runtime actions on top of `DocumentNavigator`

## D2. Selector ergonomics
- [x] support `select_paragraph(...)`
- [x] support `select_figure(...)`
- [x] support `select_near_figure(...)`
- [ ] add `select_section(...)`
- [ ] add `select_equation(...)`
- [ ] add `select_table(...)`
- [ ] add `select_heading(...)` or explicitly decide it is unnecessary
- [ ] add page-scoped variants where missing
- [ ] add relation-aware selectors such as caption/nearby direct selectors
- [ ] add tests for each new selector

## D3. Relation traversal upgrades
- [x] support generic `relations_for(...)`
- [x] support `captions_of(...)`
- [x] support `nearby_paragraphs_of(...)`
- [ ] add reverse relation helpers
- [ ] add grouped relation family helpers
- [ ] add evidence-chain traversal helpers
- [ ] add filtered incoming/outgoing relation helpers
- [ ] add richer tests for forward + reverse traversal

## D4. IR stabilization review
- [ ] review whether `DocumentMetadata` needs more normalized fields
- [ ] review whether `LocalizedEvidence` should include spans later
- [ ] review whether evidence provenance should become more structured
- [ ] review whether `DocumentRelation` should stay as one generic type or gain wrappers
- [ ] document the extraction-ready stable subset of `DocumentIR`

## D5. Extraction readiness
- [x] write repo split plan doc
- [x] establish `app/document/` as internal future extraction target
- [ ] map likely extraction files precisely
- [ ] identify remaining imports that block extraction cleanliness
- [ ] decide whether `document_handles.py` moves wholesale or gets split
- [ ] decide whether `node_handle.py` gets split
- [ ] decide whether any remaining document query helpers still live in runtime by mistake

---

# S. Agent sandbox layer

## S1. Workspace lifecycle completion
- [x] support workspace initialization
- [x] support full file read
- [x] support editable body read
- [x] support body write
- [x] support body patch
- [x] support compile
- [x] support submit-after-success
- [ ] define explicit lifecycle states for workspace/annotation editing
- [ ] record attempt count and last action explicitly
- [ ] make state transitions visible and testable

Notes:
- current workflow exists but is still method-oriented rather than fully state-oriented

## S2. Locked template protection hardening
- [x] use locked/editable region markers
- [x] reject missing required markers in fake compiler
- [x] do basic locked-structure validation in workspace
- [ ] replace heuristic string checks with exact locked-region validation
- [ ] normalize line endings before locked-region comparison
- [ ] reject any out-of-region modification, not only missing key strings
- [ ] add adversarial tests for preamble tampering and suffix tampering

## S3. Compile protocol stabilization
- [x] have `CompileResult`
- [x] have structured `CompileError`
- [x] use initial error codes (`LOCKED_REGION_MODIFICATION`, `COMPILE_VALIDATION_ERROR`)
- [ ] stabilize compile error taxonomy
- [ ] add `TEMPLATE_STRUCTURE_ERROR`
- [ ] define future `LATEX_COMPILE_ERROR`
- [ ] make repeated compile failures deterministic and test-covered
- [ ] ensure all sandbox validation failures flow through structured errors

## S4. Model-facing sandbox tool contract
- [x] expose tool-like operations through `WorkspaceHandle`
- [x] keep single-file `file.tex` design
- [x] keep structured operations primary
- [ ] write explicit sandbox tool contract doc in repo
- [ ] document call sequence for tool-first models
- [ ] document compatibility strategy for read/write-style models
- [ ] document bash fallback strategy without bypassing protections
- [ ] add tests for expected call sequences

## S5. Recovery loop readiness
- [x] support bounded retry loop in `AnnotationService`
- [x] pass compile errors into subsequent edit attempts
- [ ] preserve attempt history more explicitly
- [ ] define terminal stop conditions clearly
- [ ] surface repeated-failure state more clearly
- [ ] add tests for multi-step repair loops

## S6. Real compiler migration path
- [x] keep fake compiler as current backend
- [ ] define compiler protocol/interface explicitly
- [ ] add placeholder real compiler adapter class or protocol
- [ ] define stderr/log parsing strategy for real LaTeX compiler
- [ ] ensure backend swap would not alter tool semantics

## S7. Sandbox boundary cleanup
- [x] keep workspace/compiler code outside orchestrator
- [x] keep provider-specific prompting outside sandbox core
- [ ] review whether `AnnotationService` should be split into orchestration vs sandbox-session components
- [ ] review whether workspace state should move closer to domain models
- [ ] document exact sandbox extraction boundary if it later becomes its own module

---

## Documentation subtask status
- [x] write master implementation plan
- [x] write execution checklist
- [x] write dedicated playwright-like API spec
- [x] write dedicated sandbox contract/state-machine spec

## Immediate next task
- [ ] D2: add `select_section(...)`
- [ ] D2: add `select_table(...)`
- [ ] D2: add `select_equation(...)`

## After that
- [ ] D3: richer reverse/grouped relation helpers
- [ ] S2: exact locked-region validation
- [ ] S1: explicit sandbox lifecycle states

---

## Resume rule

After context compression:

1. read `docs/implementation_master_plan_v1.md`
2. read this checklist
3. start from the first unchecked item under `D2`
4. after each finished slice:
   - update this file
   - run tests/lint
   - commit if coherent
