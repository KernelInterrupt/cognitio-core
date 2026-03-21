from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
from typing import Literal

from pydantic import BaseModel, Field


class ProbeIssue(BaseModel):
    code: str
    message: str


class PlatformInfo(BaseModel):
    os_name: str
    kernel: str
    architecture: str
    is_wsl: bool = False
    wsl_distro: str | None = None
    docker_desktop_context: bool = False


class GpuInfo(BaseModel):
    vendor: Literal["nvidia", "amd", "intel", "unknown"] = "unknown"
    model: str | None = None
    driver_version: str | None = None
    vram_mb: int | None = None
    source: str | None = None


class EnvGpuStatus(BaseModel):
    direct_nvidia_smi_ok: bool = False
    direct_nvidia_smi_error: str | None = None
    direct_device_access: bool = False
    docker_probe_gpu_ok: bool = False


class DockerCapability(BaseModel):
    available: bool = False
    runtime: str | None = None
    supports_gpu_flag: bool = False
    nvidia_gpu_passthrough: bool = False
    vulkan_backend: bool = False
    active_probe_ran: bool = False
    active_probe_error: str | None = None


class RuntimeCapabilities(BaseModel):
    local_cpu: bool = True
    docker_nvidia_gpu: bool = False
    docker_vulkan: bool = False
    local_wsl_gpu: bool = False
    remote_inference: bool = True


class RuntimeRecommendation(BaseModel):
    recommended_runtime: Literal[
        "docker_cuda",
        "docker_cpu",
        "local_cpu",
        "remote_inference",
    ]
    reasons: list[str] = Field(default_factory=list)
    blocked_runtimes: list[ProbeIssue] = Field(default_factory=list)


class CapabilityReport(BaseModel):
    platform: PlatformInfo
    gpu: GpuInfo = Field(default_factory=GpuInfo)
    env_gpu_status: EnvGpuStatus = Field(default_factory=EnvGpuStatus)
    docker: DockerCapability = Field(default_factory=DockerCapability)
    capabilities: RuntimeCapabilities = Field(default_factory=RuntimeCapabilities)
    recommendation: RuntimeRecommendation
    issues: list[ProbeIssue] = Field(default_factory=list)


class CapabilityProbe:
    def __init__(self, *, active_docker_probe: bool = False) -> None:
        self.active_docker_probe = active_docker_probe

    def run(self) -> CapabilityReport:
        platform_info = self._probe_platform()
        gpu_info, env_gpu_status, gpu_issues = self._probe_gpu(platform_info)
        docker_info, docker_issues, docker_gpu_info = self._probe_docker(platform_info)
        merged_gpu_info = _merge_gpu_info(gpu_info, docker_gpu_info)
        env_gpu_status.docker_probe_gpu_ok = docker_info.nvidia_gpu_passthrough
        capabilities = self._derive_capabilities(platform_info, merged_gpu_info, docker_info)
        recommendation = self._recommend(platform_info, merged_gpu_info, capabilities)
        return CapabilityReport(
            platform=platform_info,
            gpu=merged_gpu_info,
            env_gpu_status=env_gpu_status,
            docker=docker_info,
            capabilities=capabilities,
            recommendation=recommendation,
            issues=[*gpu_issues, *docker_issues],
        )

    def _probe_platform(self) -> PlatformInfo:
        kernel = platform.release()
        version = platform.version()
        is_wsl = "microsoft" in kernel.lower() or "microsoft" in version.lower()
        return PlatformInfo(
            os_name=platform.system().lower(),
            kernel=kernel,
            architecture=platform.machine().lower(),
            is_wsl=is_wsl,
            wsl_distro=os.getenv("WSL_DISTRO_NAME"),
            docker_desktop_context=(
                os.path.exists("/mnt/wsl/docker-desktop")
                or bool(os.getenv("WSL_DISTRO_NAME"))
            ),
        )

    def _probe_gpu(
        self,
        platform_info: PlatformInfo,
    ) -> tuple[GpuInfo, EnvGpuStatus, list[ProbeIssue]]:
        issues: list[ProbeIssue] = []
        env_status = EnvGpuStatus(
            direct_device_access=os.path.exists("/dev/dxg") or os.path.exists("/dev/dri")
        )

        if shutil.which("nvidia-smi"):
            result = _safe_run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version,memory.total",
                    "--format=csv,noheader,nounits",
                ]
            )
            if result.returncode == 0 and result.stdout.strip():
                env_status.direct_nvidia_smi_ok = True
                parsed = _parse_nvidia_smi_csv(result.stdout)
                if parsed is not None:
                    parsed.source = "nvidia-smi"
                    return parsed, env_status, issues
            if result.stderr.strip() or result.stdout.strip():
                env_status.direct_nvidia_smi_error = (result.stderr or result.stdout).strip()
                issues.append(
                    ProbeIssue(
                        code="nvidia_smi_unavailable",
                        message=env_status.direct_nvidia_smi_error,
                    )
                )

        amd_name = _read_first_existing(
            [
                "/sys/class/drm/card0/device/product_name",
                "/sys/class/drm/card1/device/product_name",
            ]
        )
        if amd_name:
            return (
                GpuInfo(vendor="amd", model=amd_name.strip(), source="sysfs"),
                env_status,
                issues,
            )

        if platform_info.is_wsl and os.path.isdir("/usr/lib/wsl/lib"):
            libs = os.listdir("/usr/lib/wsl/lib")
            if any(name.startswith("libcuda") for name in libs):
                issues.append(
                    ProbeIssue(
                        code="wsl_gpu_libs_present_but_not_usable_here",
                        message=(
                            "WSL GPU libraries exist, but direct GPU access is "
                            "unavailable in this distro."
                        ),
                    )
                )
        return GpuInfo(), env_status, issues

    def _probe_docker(
        self,
        platform_info: PlatformInfo,
    ) -> tuple[DockerCapability, list[ProbeIssue], GpuInfo | None]:
        issues: list[ProbeIssue] = []
        if not shutil.which("docker"):
            return DockerCapability(), issues, None

        result = _safe_run(["docker", "info", "--format", "{{json .}}"])
        if result.returncode != 0 or not result.stdout.strip():
            issues.append(
                ProbeIssue(
                    code="docker_unavailable",
                    message=(result.stderr or result.stdout or "docker info failed").strip(),
                )
            )
            return DockerCapability(), issues, None

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            issues.append(
                ProbeIssue(
                    code="docker_info_parse_failed",
                    message="Failed to parse docker info JSON.",
                )
            )
            return DockerCapability(available=True), issues, None

        runtime = payload.get("DefaultRuntime") or None
        supports_gpu_flag = platform_info.os_name == "linux" and platform_info.is_wsl
        docker_info = DockerCapability(
            available=True,
            runtime=runtime,
            supports_gpu_flag=supports_gpu_flag,
            nvidia_gpu_passthrough=False,
            vulkan_backend=False,
        )
        docker_gpu_info: GpuInfo | None = None

        if self.active_docker_probe:
            docker_info.active_probe_ran = True
            probe_result = self._probe_docker_nvidia_passthrough()
            docker_info.nvidia_gpu_passthrough = probe_result.returncode == 0
            if docker_info.nvidia_gpu_passthrough:
                docker_gpu_info = _parse_nvidia_smi_csv(probe_result.stdout)
                if docker_gpu_info is not None:
                    docker_gpu_info.source = "docker-nvidia-smi"
            else:
                docker_info.active_probe_error = (
                    probe_result.stderr or probe_result.stdout or "docker gpu probe failed"
                ).strip()
                issues.append(
                    ProbeIssue(
                        code="docker_nvidia_probe_failed",
                        message=docker_info.active_probe_error,
                    )
                )

        return docker_info, issues, docker_gpu_info

    def _probe_docker_nvidia_passthrough(self) -> subprocess.CompletedProcess[str]:
        return _safe_run(
            [
                "docker",
                "run",
                "--rm",
                "--gpus",
                "all",
                "nvidia/cuda:12.4.1-base-ubuntu22.04",
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total",
                "--format=csv,noheader,nounits",
            ],
            timeout=60,
        )

    def _derive_capabilities(
        self,
        _platform_info: PlatformInfo,
        _gpu_info: GpuInfo,
        docker_info: DockerCapability,
    ) -> RuntimeCapabilities:
        local_wsl_gpu = os.path.exists("/dev/dxg") or os.path.exists("/dev/dri")
        docker_nvidia_gpu = docker_info.available and docker_info.nvidia_gpu_passthrough
        docker_vulkan = False
        return RuntimeCapabilities(
            local_cpu=True,
            docker_nvidia_gpu=docker_nvidia_gpu,
            docker_vulkan=docker_vulkan,
            local_wsl_gpu=local_wsl_gpu,
            remote_inference=True,
        )

    def _recommend(
        self,
        platform_info: PlatformInfo,
        gpu_info: GpuInfo,
        capabilities: RuntimeCapabilities,
    ) -> RuntimeRecommendation:
        blocked: list[ProbeIssue] = []
        reasons: list[str] = []
        has_sufficient_nvidia_vram = gpu_info.vram_mb is None or gpu_info.vram_mb >= 4096
        if capabilities.docker_nvidia_gpu and has_sufficient_nvidia_vram:
            reasons.append("NVIDIA GPU passthrough is available in Docker.")
            if platform_info.is_wsl:
                reasons.append(
                    "Docker Desktop on WSL2 can use the NVIDIA GPU even when "
                    "this distro cannot."
                )
            return RuntimeRecommendation(
                recommended_runtime="docker_cuda",
                reasons=reasons,
                blocked_runtimes=[
                    ProbeIssue(
                        code="docker_vulkan_not_recommended",
                        message=(
                            "Docker Vulkan is not a supported primary route on "
                            "Windows Docker Desktop."
                        ),
                    )
                ],
            )

        if gpu_info.vendor == "amd" and platform_info.is_wsl:
            blocked.append(
                ProbeIssue(
                    code="amd_windows_docker_gpu_not_supported",
                    message=(
                        "AMD GPU acceleration is not a reliable Docker Desktop "
                        "path on Windows/WSL2."
                    ),
                )
            )

        if gpu_info.vendor == "nvidia" and gpu_info.vram_mb is not None and gpu_info.vram_mb < 4096:
            blocked.append(
                ProbeIssue(
                    code="nvidia_vram_too_small",
                    message=(
                        "Detected NVIDIA GPU has too little VRAM for a "
                        "comfortable local multimodal runtime."
                    ),
                )
            )

        if blocked:
            reasons.append(
                "Falling back from local GPU acceleration due to capability "
                "constraints."
            )

        recommended = "remote_inference" if platform_info.is_wsl else "local_cpu"
        if recommended == "local_cpu":
            reasons.append("CPU fallback is the safest default on this platform.")
        else:
            reasons.append("Remote inference is the safest default on this platform.")
        return RuntimeRecommendation(
            recommended_runtime=recommended,
            reasons=reasons,
            blocked_runtimes=blocked,
        )


def _safe_run(
    args: list[str],
    *,
    timeout: int = 15,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def _read_first_existing(paths: list[str]) -> str | None:
    for path in paths:
        if os.path.exists(path):
            try:
                return open(path, encoding="utf-8").read().strip()
            except OSError:
                continue
    return None


def _parse_nvidia_smi_csv(output: str) -> GpuInfo | None:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return None
    parts = [part.strip() for part in lines[0].split(",")]
    if not parts:
        return None
    vram_mb = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None
    return GpuInfo(
        vendor="nvidia",
        model=parts[0] if parts else None,
        driver_version=parts[1] if len(parts) >= 2 else None,
        vram_mb=vram_mb,
    )


def _merge_gpu_info(primary: GpuInfo, fallback: GpuInfo | None) -> GpuInfo:
    if primary.vendor != "unknown" or fallback is None:
        return primary
    return fallback


def infer_legacy_gpu_vendor(text: str) -> Literal["nvidia", "amd", "intel", "unknown"]:
    lowered = text.lower()
    if re.search(r"(gtx|rtx|geforce|quadro|tesla)", lowered):
        return "nvidia"
    if re.search(r"(radeon|rx\s|ryzen\sai|vega)", lowered):
        return "amd"
    if "intel" in lowered:
        return "intel"
    return "unknown"
