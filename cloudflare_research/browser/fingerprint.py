"""Browser fingerprint profiles for detection avoidance.

Provides comprehensive browser fingerprinting that combines multiple
identification vectors to create convincing Chrome profiles.
"""

import random
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class FingerprintComponent(Enum):
    """Components that make up a browser fingerprint."""
    USER_AGENT = "user_agent"
    TLS_FINGERPRINT = "tls_fingerprint"
    HTTP_HEADERS = "http_headers"
    JAVASCRIPT_FEATURES = "javascript_features"
    CANVAS_FINGERPRINT = "canvas_fingerprint"
    WEBGL_FINGERPRINT = "webgl_fingerprint"
    AUDIO_FINGERPRINT = "audio_fingerprint"
    SCREEN_PROPERTIES = "screen_properties"
    TIMEZONE = "timezone"
    LANGUAGE = "language"
    PLUGINS = "plugins"
    FONTS = "fonts"


@dataclass
class ScreenProperties:
    """Screen and viewport properties."""
    screen_width: int = 1920
    screen_height: int = 1080
    available_width: int = 1920
    available_height: int = 1040
    color_depth: int = 24
    pixel_depth: int = 24
    device_pixel_ratio: float = 1.0
    orientation: str = "landscape-primary"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "width": self.screen_width,
            "height": self.screen_height,
            "availWidth": self.available_width,
            "availHeight": self.available_height,
            "colorDepth": self.color_depth,
            "pixelDepth": self.pixel_depth,
            "devicePixelRatio": self.device_pixel_ratio,
            "orientation": self.orientation,
        }


@dataclass
class JavaScriptFeatures:
    """JavaScript API availability and properties."""
    webgl_supported: bool = True
    webgl2_supported: bool = True
    canvas_supported: bool = True
    audio_context_supported: bool = True
    geolocation_supported: bool = True
    notifications_supported: bool = True
    service_worker_supported: bool = True
    indexeddb_supported: bool = True
    websocket_supported: bool = True
    webrtc_supported: bool = True
    touch_supported: bool = False
    
    # Performance API
    performance_now_supported: bool = True
    performance_timing_supported: bool = True
    
    # Storage
    local_storage_supported: bool = True
    session_storage_supported: bool = True
    
    # ES6+ features
    arrow_functions: bool = True
    async_await: bool = True
    modules: bool = True
    bigint: bool = True


@dataclass
class BrowserFingerprint:
    """
    Complete browser fingerprint profile.
    
    Combines multiple identification vectors to create a consistent
    and believable browser identity.
    """
    
    # Basic browser info
    user_agent: str
    chrome_version: str = "124.0.0.0"
    platform: str = "Win32"
    
    # Hardware/System
    screen: ScreenProperties = field(default_factory=ScreenProperties)
    cpu_cores: int = 8
    memory_gb: int = 16
    
    # Locale/Region
    timezone: str = "America/New_York"
    language: str = "en-US"
    languages: List[str] = field(default_factory=lambda: ["en-US", "en"])
    
    # JavaScript capabilities
    js_features: JavaScriptFeatures = field(default_factory=JavaScriptFeatures)
    
    # Canvas fingerprint
    canvas_hash: Optional[str] = None
    webgl_vendor: str = "Google Inc. (Intel)"
    webgl_renderer: str = "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"
    
    # Audio fingerprint
    audio_hash: Optional[str] = None
    
    # Font fingerprint
    fonts: List[str] = field(default_factory=lambda: [
        "Arial", "Arial Black", "Calibri", "Cambria", "Comic Sans MS",
        "Consolas", "Courier New", "Georgia", "Impact", "Lucida Console",
        "Microsoft Sans Serif", "Segoe UI", "Tahoma", "Times New Roman",
        "Trebuchet MS", "Verdana"
    ])
    
    # Plugin information
    plugins: List[Dict[str, str]] = field(default_factory=lambda: [
        {
            "name": "PDF Viewer",
            "filename": "internal-pdf-viewer",
            "description": "Portable Document Format"
        },
        {
            "name": "Chrome PDF Viewer",
            "filename": "mhjfbmdgcfjbbpaeojofohoefgiehjai",
            "description": ""
        },
        {
            "name": "Chromium PDF Viewer",
            "filename": "mhjfbmdgcfjbbpaeojofohoefgiehjai",
            "description": ""
        },
        {
            "name": "Microsoft Edge PDF Viewer",
            "filename": "pdfjs",
            "description": "Portable Document Format"
        },
        {
            "name": "WebKit built-in PDF",
            "filename": "internal-pdf-viewer",
            "description": "Portable Document Format"
        }
    ])
    
    # Consistency hash for correlation
    fingerprint_id: str = field(default_factory=lambda: hashlib.md5(str(random.random()).encode()).hexdigest())

    def __post_init__(self):
        """Generate consistent derived values."""
        if not self.canvas_hash:
            self.canvas_hash = self._generate_canvas_hash()
        if not self.audio_hash:
            self.audio_hash = self._generate_audio_hash()

    def _generate_canvas_hash(self) -> str:
        """Generate consistent canvas fingerprint hash."""
        # Use fingerprint_id as seed for consistency
        seed = f"{self.fingerprint_id}_{self.user_agent}_{self.webgl_renderer}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def _generate_audio_hash(self) -> str:
        """Generate consistent audio fingerprint hash."""
        seed = f"{self.fingerprint_id}_{self.user_agent}_{self.cpu_cores}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def get_navigator_properties(self) -> Dict[str, Any]:
        """Get navigator object properties."""
        return {
            "userAgent": self.user_agent,
            "platform": self.platform,
            "language": self.language,
            "languages": self.languages,
            "hardwareConcurrency": self.cpu_cores,
            "deviceMemory": self.memory_gb,
            "doNotTrack": None,
            "cookieEnabled": True,
            "onLine": True,
            "webdriver": False,  # Important for detection avoidance
        }

    def get_webgl_parameters(self) -> Dict[str, str]:
        """Get WebGL parameters."""
        return {
            "UNMASKED_VENDOR_WEBGL": self.webgl_vendor,
            "UNMASKED_RENDERER_WEBGL": self.webgl_renderer,
            "VERSION": "WebGL 1.0 (OpenGL ES 2.0 Chromium)",
            "SHADING_LANGUAGE_VERSION": "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)",
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert fingerprint to dictionary."""
        return {
            "fingerprint_id": self.fingerprint_id,
            "user_agent": self.user_agent,
            "chrome_version": self.chrome_version,
            "platform": self.platform,
            "screen": self.screen.to_dict(),
            "navigator": self.get_navigator_properties(),
            "webgl": self.get_webgl_parameters(),
            "timezone": self.timezone,
            "canvas_hash": self.canvas_hash,
            "audio_hash": self.audio_hash,
            "fonts": self.fonts,
            "plugins": self.plugins,
        }


class BrowserFingerprintManager:
    """
    Manages browser fingerprint profiles and generation.
    
    Provides consistent fingerprint generation with correlation
    between different fingerprint components.
    """

    def __init__(self):
        self._profiles: Dict[str, BrowserFingerprint] = {}
        self._load_default_profiles()

    def _load_default_profiles(self) -> None:
        """Load default fingerprint profiles."""
        # Windows Chrome 124
        self._profiles["chrome_124_windows"] = BrowserFingerprint(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            chrome_version="124.0.0.0",
            platform="Win32",
            screen=ScreenProperties(1920, 1080, 1920, 1040),
            timezone="America/New_York",
        )

        # macOS Chrome 124
        self._profiles["chrome_124_macos"] = BrowserFingerprint(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            chrome_version="124.0.0.0",
            platform="MacIntel",
            screen=ScreenProperties(2560, 1440, 2560, 1415),
            webgl_vendor="Google Inc. (Apple)",
            webgl_renderer="ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)",
            timezone="America/Los_Angeles",
        )

        # Linux Chrome 124
        self._profiles["chrome_124_linux"] = BrowserFingerprint(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            chrome_version="124.0.0.0",
            platform="Linux x86_64",
            screen=ScreenProperties(1920, 1080, 1920, 1050),
            webgl_vendor="Google Inc. (NVIDIA Corporation)",
            webgl_renderer="ANGLE (NVIDIA Corporation, NVIDIA GeForce GTX 1080/PCIe/SSE2, OpenGL 4.5.0)",
            timezone="UTC",
        )

        # Mobile Chrome 124
        self._profiles["chrome_124_mobile"] = BrowserFingerprint(
            user_agent="Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            chrome_version="124.0.0.0",
            platform="Linux armv8l",
            screen=ScreenProperties(412, 915, 412, 915, device_pixel_ratio=2.625),
            cpu_cores=8,
            memory_gb=8,
            webgl_vendor="Google Inc. (Qualcomm)",
            webgl_renderer="ANGLE (Qualcomm, Adreno (TM) 640, OpenGL ES 3.2)",
            timezone="America/New_York",
        )

    def get_profile(self, profile_name: str) -> Optional[BrowserFingerprint]:
        """Get fingerprint profile by name."""
        return self._profiles.get(profile_name)

    def get_random_profile(self, platform: Optional[str] = None) -> BrowserFingerprint:
        """Get random fingerprint profile."""
        if platform:
            matching_profiles = [
                p for name, p in self._profiles.items()
                if platform.lower() in name.lower()
            ]
            if matching_profiles:
                return random.choice(matching_profiles)
        
        return random.choice(list(self._profiles.values()))

    def create_custom_profile(self, base_profile: str = "chrome_124_windows",
                            **overrides) -> BrowserFingerprint:
        """Create custom fingerprint profile."""
        base = self._profiles.get(base_profile)
        if not base:
            raise ValueError(f"Base profile '{base_profile}' not found")

        # Create copy with overrides
        profile_dict = base.to_dict()
        profile_dict.update(overrides)

        # Create new fingerprint
        return BrowserFingerprint(
            user_agent=profile_dict.get("user_agent", base.user_agent),
            chrome_version=profile_dict.get("chrome_version", base.chrome_version),
            platform=profile_dict.get("platform", base.platform),
            timezone=profile_dict.get("timezone", base.timezone),
            language=profile_dict.get("language", base.language),
        )

    def generate_randomized_profile(self, base_profile: str = "chrome_124_windows") -> BrowserFingerprint:
        """Generate profile with subtle randomization."""
        base = self._profiles.get(base_profile)
        if not base:
            raise ValueError(f"Base profile '{base_profile}' not found")

        # Random variations
        screen_variations = [
            ScreenProperties(1920, 1080, 1920, 1040),
            ScreenProperties(1920, 1080, 1920, 1050),
            ScreenProperties(2560, 1440, 2560, 1415),
            ScreenProperties(1366, 768, 1366, 738),
            ScreenProperties(1536, 864, 1536, 834),
        ]

        timezone_variations = [
            "America/New_York", "America/Chicago", "America/Denver",
            "America/Los_Angeles", "Europe/London", "Europe/Berlin",
            "Asia/Tokyo", "Australia/Sydney"
        ]

        memory_variations = [8, 16, 32]
        cpu_variations = [4, 8, 12, 16]

        return BrowserFingerprint(
            user_agent=base.user_agent,
            chrome_version=base.chrome_version,
            platform=base.platform,
            screen=random.choice(screen_variations),
            cpu_cores=random.choice(cpu_variations),
            memory_gb=random.choice(memory_variations),
            timezone=random.choice(timezone_variations),
            language=base.language,
            webgl_vendor=base.webgl_vendor,
            webgl_renderer=base.webgl_renderer,
        )

    def list_profiles(self) -> List[str]:
        """List available profile names."""
        return list(self._profiles.keys())

    def validate_fingerprint(self, fingerprint: BrowserFingerprint) -> Dict[str, bool]:
        """Validate fingerprint for consistency."""
        checks = {
            "user_agent_matches_version": fingerprint.chrome_version in fingerprint.user_agent,
            "platform_consistent": True,  # Would check platform consistency
            "screen_realistic": fingerprint.screen.screen_width >= 800,
            "memory_reasonable": 4 <= fingerprint.memory_gb <= 64,
            "cpu_reasonable": 2 <= fingerprint.cpu_cores <= 32,
            "timezone_valid": "/" in fingerprint.timezone,
            "language_valid": "-" in fingerprint.language or len(fingerprint.language) == 2,
        }

        return checks

    def get_fingerprint_entropy(self, fingerprint: BrowserFingerprint) -> float:
        """Calculate fingerprint entropy (uniqueness)."""
        # Simplified entropy calculation
        unique_components = [
            fingerprint.user_agent,
            f"{fingerprint.screen.screen_width}x{fingerprint.screen.screen_height}",
            str(fingerprint.cpu_cores),
            str(fingerprint.memory_gb),
            fingerprint.timezone,
            fingerprint.canvas_hash,
            fingerprint.audio_hash,
        ]

        # Simple entropy estimate
        entropy = 0.0
        for component in unique_components:
            if component:
                # Rough estimate based on component complexity
                entropy += len(str(component)) * 0.1

        return min(entropy, 20.0)  # Cap at reasonable maximum


# Utility functions
def create_fingerprint_manager() -> BrowserFingerprintManager:
    """Create fingerprint manager instance."""
    return BrowserFingerprintManager()


def get_chrome_fingerprint(version: str = "124.0.0.0",
                          platform: str = "windows") -> BrowserFingerprint:
    """Get Chrome fingerprint for specified version and platform."""
    manager = BrowserFingerprintManager()
    profile_name = f"chrome_{version.split('.')[0]}_{platform.lower()}"
    
    profile = manager.get_profile(profile_name)
    if profile:
        return profile
    
    # Fallback to default
    return manager.get_profile("chrome_124_windows")


def randomize_fingerprint(base_fingerprint: BrowserFingerprint) -> BrowserFingerprint:
    """Create randomized variant of fingerprint."""
    # Create slight variations
    variations = {
        "cpu_cores": random.choice([4, 6, 8, 12, 16]),
        "memory_gb": random.choice([8, 16, 32]),
        "timezone": random.choice([
            "America/New_York", "America/Chicago", "Europe/London", "UTC"
        ])
    }
    
    # Create new fingerprint with variations
    new_fingerprint = BrowserFingerprint(
        user_agent=base_fingerprint.user_agent,
        chrome_version=base_fingerprint.chrome_version,
        platform=base_fingerprint.platform,
        screen=base_fingerprint.screen,
        cpu_cores=variations["cpu_cores"],
        memory_gb=variations["memory_gb"],
        timezone=variations["timezone"],
        language=base_fingerprint.language,
        webgl_vendor=base_fingerprint.webgl_vendor,
        webgl_renderer=base_fingerprint.webgl_renderer,
    )
    
    return new_fingerprint