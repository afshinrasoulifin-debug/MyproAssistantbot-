
"""Tests for utils/fingerprint_engine.py — Unified Fingerprint Consistency Engine."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.fingerprint_engine import (
    AudioFingerprintGenerator,
    BrowserFamily,
    CanvasNoiseGenerator,
    FingerprintEngine,
    FingerprintValidator,
    FingerprintIssue,
    FONT_PROFILES,
    GPU_DATABASE,
    HARDWARE_PROFILES,
    OSType,
    SCREEN_PROFILES,
    UnifiedFingerprint,
    WebGLFingerprintGenerator,
    fingerprint_engine,
)


# ═══════════════════════════════════════════════════════════
# GPU Database Tests
# ═══════════════════════════════════════════════════════════

class TestGPUDatabase:
    def test_has_nvidia_profiles(self):
        assert "windows_nvidia" in GPU_DATABASE
        assert len(GPU_DATABASE["windows_nvidia"]) >= 4

    def test_has_amd_profiles(self):
        assert "windows_amd" in GPU_DATABASE
        assert len(GPU_DATABASE["windows_amd"]) >= 2

    def test_has_intel_profiles(self):
        assert "windows_intel" in GPU_DATABASE

    def test_has_macos_profiles(self):
        assert "macos_apple" in GPU_DATABASE

    def test_has_linux_profiles(self):
        assert "linux_mesa" in GPU_DATABASE

    def test_gpu_to_dict(self):
        gpu = GPU_DATABASE["windows_nvidia"][0]
        d = gpu.to_dict()
        assert "vendor" in d
        assert "renderer" in d
        assert "max_texture_size" in d


# ═══════════════════════════════════════════════════════════
# Screen / Font / Hardware Tests
# ═══════════════════════════════════════════════════════════

class TestScreenProfiles:
    def test_windows_screens(self):
        assert "windows" in SCREEN_PROFILES
        assert len(SCREEN_PROFILES["windows"]) >= 4

    def test_macos_retina(self):
        for screen in SCREEN_PROFILES["macos"]:
            assert screen.device_pixel_ratio >= 2.0

    def test_screen_to_dict(self):
        screen = SCREEN_PROFILES["windows"][0]
        d = screen.to_dict()
        assert d["width"] == 1920


class TestFontProfiles:
    def test_windows_has_segoe(self):
        assert "Segoe UI" in FONT_PROFILES["windows"]

    def test_macos_has_helvetica(self):
        assert "Helvetica Neue" in FONT_PROFILES["macos"]

    def test_linux_has_dejavu(self):
        assert "DejaVu Sans" in FONT_PROFILES["linux"]


# ═══════════════════════════════════════════════════════════
# Canvas / Audio / WebGL Noise Tests
# ═══════════════════════════════════════════════════════════

class TestCanvasNoiseGenerator:
    def test_generate_noise_script(self):
        script = CanvasNoiseGenerator.generate_noise_script(12345)
        assert "toDataURL" in script
        assert "getImageData" in script

    def test_deterministic_hash(self):
        h1 = CanvasNoiseGenerator.compute_expected_hash(12345)
        h2 = CanvasNoiseGenerator.compute_expected_hash(12345)
        assert h1 == h2

    def test_different_seeds_different_hashes(self):
        h1 = CanvasNoiseGenerator.compute_expected_hash(111)
        h2 = CanvasNoiseGenerator.compute_expected_hash(222)
        assert h1 != h2

    def test_script_is_iife(self):
        script = CanvasNoiseGenerator.generate_noise_script(1)
        assert "(() =>" in script


class TestAudioFingerprintGenerator:
    def test_generate_noise_script(self):
        script = AudioFingerprintGenerator.generate_noise_script(42)
        assert "AudioContext" in script
        assert "createOscillator" in script

    def test_deterministic_hash(self):
        h1 = AudioFingerprintGenerator.compute_expected_hash(42)
        h2 = AudioFingerprintGenerator.compute_expected_hash(42)
        assert h1 == h2


class TestWebGLFingerprintGenerator:
    def test_generate_override_script(self):
        gpu = GPU_DATABASE["windows_nvidia"][0]
        script = WebGLFingerprintGenerator.generate_override_script(gpu, 123)
        assert "getParameter" in script
        assert gpu.unmasked_vendor in script
        assert "WebGL2" in script


# ═══════════════════════════════════════════════════════════
# Unified Fingerprint Tests
# ═══════════════════════════════════════════════════════════

class TestUnifiedFingerprint:
    def test_get_all_scripts(self):
        fp = UnifiedFingerprint(
            profile_id="test", seed=1,
            os=OSType.WINDOWS, browser=BrowserFamily.CHROME,
            gpu=GPU_DATABASE["windows_nvidia"][0],
            screen=SCREEN_PROFILES["windows"][0],
            fonts=FONT_PROFILES["windows"],
            hardware=HARDWARE_PROFILES["mid_desktop"],
            canvas_script="a", audio_script="b", webgl_script="c",
        )
        assert len(fp.get_all_scripts()) == 3

    def test_to_dict(self):
        fp = UnifiedFingerprint(
            profile_id="test", seed=1,
            os=OSType.WINDOWS, browser=BrowserFamily.CHROME,
            gpu=GPU_DATABASE["windows_nvidia"][0],
            screen=SCREEN_PROFILES["windows"][0],
            fonts=FONT_PROFILES["windows"],
            hardware=HARDWARE_PROFILES["mid_desktop"],
        )
        d = fp.to_dict()
        assert d["os"] == "windows"
        assert d["browser"] == "chrome"
        assert "gpu" in d


# ═══════════════════════════════════════════════════════════
# Fingerprint Validator Tests
# ═══════════════════════════════════════════════════════════

class TestFingerprintValidator:
    def test_valid_windows_chrome(self):
        fp = UnifiedFingerprint(
            profile_id="t", seed=1,
            os=OSType.WINDOWS, browser=BrowserFamily.CHROME,
            gpu=GPU_DATABASE["windows_nvidia"][0],
            screen=SCREEN_PROFILES["windows"][0],
            fonts=FONT_PROFILES["windows"],
            hardware=HARDWARE_PROFILES["mid_desktop"],
        )
        issues = FingerprintValidator.validate(fp)
        assert len(issues) == 0

    def test_invalid_windows_apple_gpu(self):
        fp = UnifiedFingerprint(
            profile_id="t", seed=1,
            os=OSType.WINDOWS, browser=BrowserFamily.CHROME,
            gpu=GPU_DATABASE["macos_apple"][0],
            screen=SCREEN_PROFILES["windows"][0],
            fonts=FONT_PROFILES["windows"],
            hardware=HARDWARE_PROFILES["mid_desktop"],
        )
        issues = FingerprintValidator.validate(fp)
        critical = [i for i in issues if i.severity == "critical"]
        assert len(critical) >= 1

    def test_safari_on_windows_invalid(self):
        fp = UnifiedFingerprint(
            profile_id="t", seed=1,
            os=OSType.WINDOWS, browser=BrowserFamily.SAFARI,
            gpu=GPU_DATABASE["windows_nvidia"][0],
            screen=SCREEN_PROFILES["windows"][0],
            fonts=FONT_PROFILES["windows"],
            hardware=HARDWARE_PROFILES["mid_desktop"],
        )
        issues = FingerprintValidator.validate(fp)
        assert any("Safari" in i.detail for i in issues)

    def test_valid_macos_safari(self):
        fp = UnifiedFingerprint(
            profile_id="t", seed=1,
            os=OSType.MACOS, browser=BrowserFamily.SAFARI,
            gpu=GPU_DATABASE["macos_apple"][0],
            screen=SCREEN_PROFILES["macos"][0],
            fonts=FONT_PROFILES["macos"],
            hardware=HARDWARE_PROFILES["macbook"],
        )
        critical = [i for i in FingerprintValidator.validate(fp) if i.severity == "critical"]
        assert len(critical) == 0

    def test_missing_windows_font_warning(self):
        fp = UnifiedFingerprint(
            profile_id="t", seed=1,
            os=OSType.WINDOWS, browser=BrowserFamily.CHROME,
            gpu=GPU_DATABASE["windows_nvidia"][0],
            screen=SCREEN_PROFILES["windows"][0],
            fonts=["Arial", "Courier New"],
            hardware=HARDWARE_PROFILES["mid_desktop"],
        )
        issues = FingerprintValidator.validate(fp)
        assert any(i.vector == "fonts" for i in issues)

    def test_issue_to_dict(self):
        issue = FingerprintIssue(vector="gpu_os", detail="test", severity="critical")
        d = issue.to_dict()
        assert d["severity"] == "critical"


# ═══════════════════════════════════════════════════════════
# FingerprintEngine (Main) Tests
# ═══════════════════════════════════════════════════════════

class TestFingerprintEngine:
    def test_singleton(self):
        assert fingerprint_engine is not None

    def test_version(self):
        assert "TITAN" in FingerprintEngine.VERSION

    def test_generate_windows_chrome(self):
        engine = FingerprintEngine()
        fp = engine.generate(os=OSType.WINDOWS, browser=BrowserFamily.CHROME)
        assert fp.os == OSType.WINDOWS
        assert fp.browser == BrowserFamily.CHROME
        assert fp.profile_id
        assert len(fp.fonts) > 5
        assert fp.canvas_hash

    def test_generate_with_seed(self):
        engine = FingerprintEngine()
        fp1 = engine.generate(seed=42)
        fp2 = engine.generate(seed=42)
        assert fp1.profile_id == fp2.profile_id
        assert fp1.canvas_hash == fp2.canvas_hash

    def test_generate_different_seeds(self):
        engine = FingerprintEngine()
        fp1 = engine.generate(seed=1)
        fp2 = engine.generate(seed=2)
        assert fp1.profile_id != fp2.profile_id

    def test_generate_macos_safari(self):
        engine = FingerprintEngine()
        fp = engine.generate(os=OSType.MACOS, browser=BrowserFamily.SAFARI)
        assert "Apple" in fp.gpu.unmasked_vendor or "Apple" in fp.gpu.vendor

    def test_generate_with_gpu_class(self):
        engine = FingerprintEngine()
        fp = engine.generate(os=OSType.WINDOWS, gpu_class="amd")
        assert "AMD" in fp.gpu.unmasked_vendor or "AMD" in fp.gpu.renderer

    def test_generate_with_hardware_class(self):
        engine = FingerprintEngine()
        fp = engine.generate(os=OSType.WINDOWS, hardware_class="high_end_desktop")
        assert fp.hardware["hardware_concurrency"] == 16

    def test_scripts_generated(self):
        engine = FingerprintEngine()
        fp = engine.generate()
        assert fp.canvas_script
        assert fp.audio_script
        assert fp.webgl_script
        assert len(fp.get_all_scripts()) == 3

    def test_validate_generated_profile(self):
        engine = FingerprintEngine()
        for os_type in [OSType.WINDOWS, OSType.MACOS, OSType.LINUX]:
            browser = BrowserFamily.SAFARI if os_type == OSType.MACOS else BrowserFamily.CHROME
            fp = engine.generate(os=os_type, browser=browser)
            critical = [i for i in engine.validate(fp) if i.severity == "critical"]
            assert len(critical) == 0, f"{os_type}: {[i.detail for i in critical]}"

    def test_get_gpu_for_os(self):
        engine = FingerprintEngine()
        win_gpus = engine.get_gpu_for_os(OSType.WINDOWS)
        assert any("nvidia" in g for g in win_gpus)

    def test_get_stats(self):
        engine = FingerprintEngine()
        engine.generate()
        engine.generate()
        stats = engine.get_stats()
        assert stats["fingerprints_generated"] == 2
        assert stats["gpu_profiles"] > 0


