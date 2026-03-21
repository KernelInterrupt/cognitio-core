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

## Probe order

The probe now follows a layered strategy.

### 1. Direct environment probe
It first tries the simplest thing:
- run `nvidia-smi` in the current environment
- inspect direct GPU device visibility such as `/dev/dxg` or `/dev/dri`

This answers:
- can the current shell/distro directly use the GPU?
- if not, what error appears?

### 2. Passive Docker probe
Then it inspects Docker availability via `docker info`.

This answers:
- is Docker available?
- what runtime is active?
- is this a Docker Desktop / WSL-like environment?

### 3. Optional active Docker GPU probe
If enabled, it additionally runs a real containerized `nvidia-smi` probe.

This answers:
- can Docker actually passthrough the NVIDIA GPU?
- if yes, what GPU/VRAM does the container see?

## Outputs

`CapabilityProbe` produces:
- platform info
- merged GPU info
- `env_gpu_status`
- Docker capability snapshot
- derived runtime capabilities
- final runtime recommendation
- blocked runtime reasons

## Important distinction

The report separates:
- **direct environment GPU visibility**
- **Docker runtime GPU visibility**

This matters on WSL2 because the current distro may fail direct `nvidia-smi` while Docker Desktop can still successfully expose the NVIDIA GPU inside containers.

## Current recommendation policy

### Prefer `docker_cuda`
When:
- Docker is available
- Docker NVIDIA passthrough is confirmed
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
