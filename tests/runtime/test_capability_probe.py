from app.runtime.capability_probe import CapabilityProbe, PlatformInfo, infer_legacy_gpu_vendor


def test_infer_legacy_gpu_vendor_detects_nvidia() -> None:
    assert infer_legacy_gpu_vendor('GeForce GTX 750 Ti') == 'nvidia'


def test_infer_legacy_gpu_vendor_detects_amd() -> None:
    assert infer_legacy_gpu_vendor('Radeon 780M') == 'amd'


def test_recommend_docker_cuda_when_nvidia_passthrough_available() -> None:
    probe = CapabilityProbe()
    platform_info = PlatformInfo(
        os_name='linux',
        kernel='6.6.87.2-microsoft-standard-WSL2',
        architecture='x86_64',
        is_wsl=True,
        wsl_distro='Ubuntu-22.04',
        docker_desktop_context=True,
    )
    report = probe._recommend(  # noqa: SLF001
        platform_info,
        gpu_info=type('Gpu', (), {'vendor': 'nvidia', 'vram_mb': 8192})(),
        capabilities=type('Caps', (), {'docker_nvidia_gpu': True})(),
    )
    assert report.recommended_runtime == 'docker_cuda'


def test_recommend_remote_for_amd_on_wsl() -> None:
    probe = CapabilityProbe()
    platform_info = PlatformInfo(
        os_name='linux',
        kernel='6.6.87.2-microsoft-standard-WSL2',
        architecture='x86_64',
        is_wsl=True,
        wsl_distro='Ubuntu-22.04',
        docker_desktop_context=True,
    )
    report = probe._recommend(  # noqa: SLF001
        platform_info,
        gpu_info=type('Gpu', (), {'vendor': 'amd', 'vram_mb': 16384})(),
        capabilities=type('Caps', (), {'docker_nvidia_gpu': False})(),
    )
    assert report.recommended_runtime == 'remote_inference'
    assert report.blocked_runtimes
