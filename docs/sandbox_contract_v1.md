# Sandbox Contract v1

This document defines the intended technical contract for the annotation sandbox.

It is meant to go beyond a high-level roadmap and specify:

- state model
- component boundaries
- tool contract
- locked-template rules
- compile loop behavior
- compatibility targets for different model styles

This document should be read together with:

- `docs/implementation_master_plan_v1.md`
- `docs/execution_checklist_v1.md`
- `docs/playwright_like_api_v1.md`

---

## 1. Core sandbox goal

The sandbox exists to support annotation editing in a way that is:

- constrained
- recoverable
- model-friendly
- template-safe

The sandbox is **not** a general execution environment.
It is a focused annotation-editing subsystem.

---

## 2. Frozen assumptions

These assumptions are currently fixed.

1. one annotation -> one workspace
2. one workspace -> one virtual editable file
3. that file is `file.tex`
4. the LaTeX template is owned by the system, not by the model
5. the model edits only the body/editable region
6. compile returns structured results
7. failed compile can feed the next repair attempt
8. structured tools are primary
9. bash is fallback only

---

## 3. Current implementation baseline

### Files

- `app/sandbox/templates.py`
- `app/sandbox/workspace.py`
- `app/sandbox/handle.py`
- `app/sandbox/compiler.py`
- `app/services/annotation_service.py`
- `app/domain/annotation.py`

### Current behavior

Already present:
- initialize workspace
- write template into `file.tex`
- read full file
- read editable region
- write editable region
- patch editable region
- compile through the current temporary `FakeCompiler` backend
- retrieve structured compile errors
- submit only after successful compile
- bounded provider retry loop in `AnnotationService`

Important clarification:
- the fake compiler is only a workflow-testing backend
- the target system should compile through a real LaTeX toolchain, likely via Docker or another isolated backend path
- the long-term goal is real multilingual LaTeX compilation behind the same structured interface

Current weak spots:
- sandbox state is not explicit enough
- locked-region validation is still heuristic
- compiler error taxonomy is still too coarse
- tool contract is implied by code, not formally documented

---

## 4. Component boundaries

## 4.1 `templates.py`
Responsible for:
- marker constants
- default locked template
- future template versioning if needed

Should not own:
- runtime state
- compile behavior
- provider logic

## 4.2 `workspace.py`
Responsible for:
- workspace directory ownership
- `file.tex` creation
- reading full file
- extracting editable region
- replacing editable region
- validating locked-region integrity

Should not own:
- provider prompting
- retry logic
- orchestration policy

## 4.3 `compiler.py`
Responsible for:
- compile backend abstraction
- compile result generation
- structured error return

Should not own:
- workspace persistence
- provider loop logic

## 4.4 `handle.py`
Responsible for:
- model-facing operational surface
- workspace + compiler composition
- current file/body/compile interaction

Should not own:
- provider prompting
- global orchestration policy

## 4.5 `annotation_service.py`
Responsible for:
- edit/compile/fix orchestration
- attempt loop
- passing compile errors back into provider edit calls

Should not own:
- low-level locked-region parsing
- template definition

---

## 5. State model

The sandbox should move toward an explicit state machine.

## 5.1 Proposed states

### `initialized`
Workspace exists and `file.tex` has been created from the template.

### `editing`
The model has read or modified the body but there is not yet a successful compile.

### `compile_failed`
A compile attempt completed and returned errors.

### `compiled`
The latest compile attempt succeeded.

### `submitted`
The compiled annotation has been accepted/finalized.

---

## 5.2 State transitions

Allowed transitions:

```text
initialized -> editing
editing -> compile_failed
editing -> compiled
compile_failed -> editing
compile_failed -> compiled
compiled -> submitted
```

Disallowed transitions:

```text
initialized -> submitted
compile_failed -> submitted
submitted -> editing
```

---

## 5.3 State ownership

Preferred direction:

- transient workspace state lives on the workspace/handle side
- durable annotation outcome is reflected in `Annotation`

This means the code should later clarify:
- handle-local runtime state
- annotation-domain state
- compile-result state

---

## 6. Locked template contract

The system owns:

- `\documentclass`
- `\usepackage`
- macro declarations
- document start/end structure
- marker layout

The model owns only the editable body region between:

- `EDITABLE_START`
- `EDITABLE_END`

### Required safety rule

A compile attempt must fail if any locked region changes, even if some expected strings still remain.

That means the correct final direction is **exact locked-region comparison**, not string-presence heuristics.

### Preferred validation algorithm

1. initialize workspace from canonical template
2. split current file into:
   - locked prefix
   - editable body
   - locked suffix
3. normalize line endings
4. compare locked prefix and suffix to expected canonical values
5. if mismatch, return structured locked-region error

---

## 7. Tool contract

The public model-facing operations should remain:

```python
read_file()
read_body()
write_body(content)
patch_body(old, new)
compile_annotation()
get_compile_errors()
submit_annotation()
```

### Semantics

#### `read_file()`
Return full `file.tex`.
Used when a model wants full visibility.

#### `read_body()`
Return editable body only.
Preferred for structured editing.

#### `write_body(content)`
Replace editable region only.
Must not alter locked regions.

#### `patch_body(old, new)`
Patch editable region only.
Must not alter locked regions.

#### `compile_annotation()`
Run locked-region validation first, then compiler backend.
Return `CompileResult`.

#### `get_compile_errors()`
Return stable structured errors from last compile attempt.

#### `submit_annotation()`
Allowed only after successful compile.

---

## 8. Error taxonomy target

Current codes:
- `LOCKED_REGION_MODIFICATION`
- `COMPILE_VALIDATION_ERROR`

Target expanded families:
- `LOCKED_REGION_MODIFICATION`
- `TEMPLATE_STRUCTURE_ERROR`
- `ANNOTATION_SCHEMA_ERROR`
- `LATEX_COMPILE_ERROR`
- `SUBMISSION_PRECONDITION_ERROR`

Guideline:
- orchestration/provider layers should branch on `code`, not on raw message parsing

---

## 9. Retry / recovery loop

The sandbox is designed for iterative repair.

### Current loop
Roughly:
1. initialize workspace
2. provider edits file/body
3. compile
4. if failure, pass errors back into next attempt
5. stop on success or attempt limit

### Required next improvements
- explicit attempt counter
- clearer terminal stop conditions
- stable preservation of compile history
- better repeated-failure visibility

### Stop conditions to formalize
- successful compile -> submit
- max attempts reached -> return failed result
- repeated locked-region failure -> still bounded by attempts for now
- provider requests submit before successful compile -> fail explicitly

---

## 10. Compatibility with model styles

## 10.1 Tool-first models
Preferred path.
They should call the structured operations directly.

## 10.2 Read/write-oriented models
Still supported.
They should conceptually interact with:
- full file view when needed
- body-only editing when possible

## 10.3 Bash-oriented models
Allowed only as fallback.
If introduced later, bash wrappers must map back to the same constrained body/file operations and must not bypass locked-region checks.

---

## 11. Real compiler migration path

The fake compiler is acceptable now because it lets us stabilize the workflow.

Future direction:

```text
Compiler protocol
  -> FakeCompiler
  -> RealLatexCompiler
```

Requirements for future real compiler path:
- same `CompileResult` shape
- same error object family
- same workspace contract
- no change to model-facing tool semantics

---

## 12. Immediate implementation implications

The next sandbox work should prioritize:

1. exact locked-region validation
2. explicit state machine
3. compile error taxonomy stabilization
4. documented tool call sequence
5. stronger multi-attempt repair-loop tests

