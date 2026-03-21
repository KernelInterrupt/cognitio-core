from subprocess import CompletedProcess

import pytest

from app.runtime.capability_probe import (
    CapabilityProbe,
    DockerCapability,
    EnvGpuStatus,
    GpuInfo,
    PlatformInfo,
    _merge_gpu_info,
    _parse_nvidia_smi_csv,
    infer_legacy_gpu_vendor,
)


def test_infer_legacy_gpu_vendor_detects_nvidia() -> None:
    assert infer_legacy_gpu_vendor("GeForce GTX 750 Ti") == "nvidia"


def test_infer_legacy_gpu_vendor_detects_amd() -> None:
    assert infer_legacy_gpu_vendor("Radeon 780M") == "amd"


def test_parse_nvidia_smi_csv_parses_basic_fields() -> None:
    parsed = _parse_nvidia_smi_csv("RTX 4060 Laptop GPU, 580.97, 8188\n")
    assert parsed is not None
    assert parsed.vendor == "nvidia"
    assert parsed.model == "RTX 4060 Laptop GPU"
    assert parsed.vram_mb == 8188


def test_merge_gpu_info_prefers_fallback_when_primary_unknown() -> None:
    merged = _merge_gpu_info(
        GpuInfo(),
        GpuInfo(vendor="nvidia", model="RTX 4060 Laptop GPU", vram_mb=8188),
    )
    assert merged.vendor == "nvidia"


def test_recommend_docker_cuda_when_nvidia_passthrough_available() -> None:
    probe = CapabilityProbe()
    platform_info = PlatformInfo(
        os_name="linux",
        kernel="6.6.87.2-microsoft-standard-WSL2",
        architecture="x86_64",
        is_wsl=True,
        wsl_distro="Ubuntu-22.04",
        docker_desktop_context=True,
    )
    report = probe._recommend(  # noqa: SLF001
        platform_info,
        gpu_info=GpuInfo(vendor="nvidia", vram_mb=8192),
        capabilities=type("Caps", (), {"docker_nvidia_gpu": True})(),
    )
    assert report.recommended_runtime == "docker_cuda"


def test_recommend_remote_for_amd_on_wsl() -> None:
    probe = CapabilityProbe()
    platform_info = PlatformInfo(
        os_name="linux",
        kernel="6.6.87.2-microsoft-standard-WSL2",
        architecture="x86_64",
        is_wsl=True,
        wsl_distro="Ubuntu-22.04",
        docker_desktop_context=True,
    )
    report = probe._recommend(  # noqa: SLF001
        platform_info,
        gpu_info=GpuInfo(vendor="amd", vram_mb=16384),
        capabilities=type("Caps", (), {"docker_nvidia_gpu": False})(),
    )
    assert report.recommended_runtime == "remote_inference"
    assert report.blocked_runtimes


def test_derive_capabilities_uses_active_docker_probe_result() -> None:
    probe = CapabilityProbe(active_docker_probe=True)
    caps = probe._derive_capabilities(  # noqa: SLF001
        PlatformInfo(
            os_name="linux",
            kernel="6.6.87.2-microsoft-standard-WSL2",
            architecture="x86_64",
            is_wsl=True,
            wsl_distro="Ubuntu-22.04",
            docker_desktop_context=True,
        ),
        GpuInfo(),
        DockerCapability(available=True, nvidia_gpu_passthrough=True),
    )
    assert caps.docker_nvidia_gpu is True


def test_probe_run_uses_docker_gpu_info_when_local_env_cannot_access_gpu() -> None:
    probe = CapabilityProbe(active_docker_probe=True)
    probe._probe_platform = lambda: PlatformInfo(  # type: ignore[method-assign]
        os_name="linux",
        kernel="6.6.87.2-microsoft-standard-WSL2",
        architecture="x86_64",
        is_wsl=True,
        wsl_distro="Ubuntu-22.04",
        docker_desktop_context=True,
    )
    probe._probe_gpu = lambda _platform: (  # type: ignore[method-assign]
        GpuInfo(),
        EnvGpuStatus(
            direct_nvidia_smi_ok=False,
            direct_nvidia_smi_error="blocked",
            direct_device_access=False,
            docker_probe_gpu_ok=False,
        ),
        [],
    )
    probe._probe_docker = lambda _platform: (  # type: ignore[method-assign]
        DockerCapability(
            available=True,
            runtime="runc",
            supports_gpu_flag=True,
            nvidia_gpu_passthrough=True,
            active_probe_ran=True,
        ),
        [],
        GpuInfo(
            vendor="nvidia",
            model="RTX 4060 Laptop GPU",
            driver_version="580.97",
            vram_mb=8188,
            source="docker-nvidia-smi",
        ),
    )

    report = probe.run()

    assert report.gpu.vendor == "nvidia"
    assert report.env_gpu_status.direct_nvidia_smi_ok is False
    assert report.env_gpu_status.docker_probe_gpu_ok is True
    assert report.recommendation.recommended_runtime == "docker_cuda"


def test_probe_docker_marks_active_probe_success(monkeypatch: pytest.MonkeyPatch) -> None:
    probe = CapabilityProbe(active_docker_probe=True)
    monkeypatch.setattr(
        "app.runtime.capability_probe.shutil.which",
        lambda _name: "/usr/bin/docker",
    )
    monkeypatch.setattr(
        "app.runtime.capability_probe._safe_run",
        lambda args, timeout=15: CompletedProcess(
            args=args,
            returncode=0,
            stdout='{"DefaultRuntime":"runc"}',
            stderr="",
        )
        if args[:2] == ["docker", "info"]
        else CompletedProcess(
            args=args,
            returncode=0,
            stdout="RTX 4060 Laptop GPU, 580.97, 8188\n",
            stderr="",
        ),
    )
    docker_info, issues, gpu_info = probe._probe_docker(  # noqa: SLF001
        PlatformInfo(
            os_name="linux",
            kernel="6.6.87.2-microsoft-standard-WSL2",
            architecture="x86_64",
            is_wsl=True,
            wsl_distro="Ubuntu-22.04",
            docker_desktop_context=True,
        )
    )

    assert not issues
    assert docker_info.active_probe_ran is True
    assert docker_info.nvidia_gpu_passthrough is True
    assert gpu_info is not None
    assert gpu_info.model == "RTX 4060 Laptop GPU"
