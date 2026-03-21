# Runtime Capability Probe v1

## Goal

Detect what runtime path should be recommended on the current machine instead of assuming that any visible GPU is usable.

## Why

A machine can have a GPU and still be unsuitable for our local runtime path because of:
- unsupported vendor/runtime combination
- too little VRAM
- Docker Desktop platform limitations
- WSL distro limitations
- driver/runtime mismatch

## Outputs

`CapabilityProbe` produces:
- platform info
- detected GPU info
- Docker capability snapshot
- derived runtime capabilities
- final runtime recommendation
- blocked runtime reasons

## Current recommendation policy

### Prefer `docker_cuda`
When:
- Docker is available
- platform is WSL2/Linux Docker Desktop context
- GPU vendor is NVIDIA
- VRAM is sufficient

### Prefer `remote_inference`
When:
- the platform is WSL2
- but Docker GPU support is not on a good path
- especially for AMD-only Windows/WSL2 users

### Prefer `local_cpu`
When:
- platform is simpler/non-WSL
- and no strong GPU/container route is detected

## Important product implication

This probe exists because deployment should be based on **usable runtime capability**, not merely on raw hardware presence.
