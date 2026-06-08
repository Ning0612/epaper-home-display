from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass, field
from typing import get_type_hints

import yaml


@dataclass
class MQTTConfig:
    broker_host: str = "localhost"
    broker_port: int = 1883
    client_id: str = "epaper-home-display"
    username: str = ""
    password: str = ""


@dataclass
class WeatherConfig:
    api_key: str = ""
    lat: float = 25.05       # Taipei default
    lon: float = 121.53
    units: str = "metric"
    fetch_interval_seconds: int = 600


@dataclass
class DHT22Config:
    gpio_pin: int = 4
    use_mock: bool = False


@dataclass
class LightConfig:
    spi_bus: int = 0
    spi_device: int = 1          # CE1; CE0 is reserved for e-Paper display
    adc_channel: int = 0
    bright_threshold: int = 500
    use_mock: bool = False


@dataclass
class ButtonConfig:
    gpio_pins: list[int] = field(default_factory=lambda: [5, 6, 27, 22])
    use_mock: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.gpio_pins, list) or len(self.gpio_pins) < 4:
            raise ValueError(
                f"sensors.button.gpio_pins must be a list of at least 4 integers, got: {self.gpio_pins!r}"
            )
        self.gpio_pins = [int(p) for p in self.gpio_pins]


@dataclass
class SensorsConfig:
    dht22: DHT22Config = field(default_factory=DHT22Config)
    light: LightConfig = field(default_factory=LightConfig)
    button: ButtonConfig = field(default_factory=ButtonConfig)


_COLOR_MODELS: frozenset[str] = frozenset({"epd7in3e"})
_SUPPORTED_DISPLAY_MODELS: frozenset[str] = frozenset({"epd7in3e", "epd7in5_V2", "mock"})
# Trigger fires this many seconds before each N-minute boundary; lag = 60 - trigger_second.
_MODEL_TRIGGER_SECOND: dict[str, int] = {
    "epd7in3e":   40,   # ACeP 7-color, full refresh ~20s
    "epd7in5_V2": 57,   # B&W, fast refresh ~0.3s (full ~2s)
    "mock":       57,
}


@dataclass
class DisplayConfig:
    model: str = "epd7in3e"
    use_mock: bool = False
    dashboard_interval_minutes: int = 5  # dashboard refresh interval; must be a divisor of 60
    full_refresh_every: int = 10          # full refresh every N updates; partial refresh otherwise

    def __post_init__(self) -> None:
        if self.model not in _SUPPORTED_DISPLAY_MODELS:
            raise ValueError(
                f"display.model must be one of {sorted(_SUPPORTED_DISPLAY_MODELS)}, got: {self.model!r}"
            )
        if self.dashboard_interval_minutes < 1 or 60 % self.dashboard_interval_minutes != 0:
            raise ValueError(
                f"display.dashboard_interval_minutes must be a divisor of 60 "
                f"(1,2,3,4,5,6,10,12,15,20,30,60), got: {self.dashboard_interval_minutes}"
            )

    @property
    def dashboard_trigger_second(self) -> int:
        return _MODEL_TRIGGER_SECOND.get(self.model, 57)

    @property
    def is_color(self) -> bool:
        return self.model in _COLOR_MODELS


@dataclass
class VoiceConfig:
    enabled: bool = True
    player: str = "aplay"
    sounds_dir: str = "assets/sounds"
    tts_engine: str = "espeak-ng"   # "espeak-ng" | "none"
    tts_language: str = "zh"        # espeak-ng voice identifier
    tts_speed: int = 130            # espeak-ng -s (words per minute)


@dataclass
class DiscordConfig:
    webhook_url: str = ""
    notify_device_online: bool = True
    notify_session_end: bool = True
    session_end_min_minutes: int = 5
    notify_daily_summary: bool = True
    daily_summary_time: str = "23:00"


@dataclass
class StorageConfig:
    db_path: str = "data/epaper-home-display.db"


@dataclass
class WebUIConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    password_hash: str = ""
    session_secret: str = ""


@dataclass
class ImagesConfig:
    storage_dir: str = "data/images"
    max_count: int = 50
    max_upload_bytes: int = 15_728_640   # 15 MB
    max_pixels: int = 25_000_000         # 25 MP; 100 MP would exhaust Pi Zero 2W RAM
    allowed_formats: list[str] = field(
        default_factory=lambda: ["JPEG", "PNG", "WEBP", "GIF", "BMP"]
    )
    carousel_enabled: bool = False
    carousel_interval_refreshes: int = 10  # advance every N dashboard refreshes
    carousel_mode: str = "sequential"      # "sequential" | "random"


@dataclass
class OutdoorAgentConfig:
    snapshot_url: str = ""                   # e.g. "http://faceguard.local/snapshot"
    snapshot_timeout_sec: float = 2.5
    alert_page_enabled: bool = True
    alert_page_timeout_sec: int = 120        # return to dashboard after N seconds with no new alert


_AP_STATUS_FILE = "/tmp/epaper-ap-mode.json"        # shared constant with wifi_manager.sh
_WIFI_SCAN_CACHE_FILE = "/tmp/epaper-wifi-scan-cache.txt"  # pre-scan cache written before AP starts


@dataclass
class WifiConfig:
    ap_ssid: str = "EpaperSetup"
    ap_password: str = "epaper123"   # AP 熱點密碼，至少 8 個字元（建議修改）
    connect_timeout: int = 30       # 開機等待 WiFi 連線的秒數
    monitor_interval: int = 10      # 定期偵測 WiFi 模式的間隔（秒）


@dataclass
class ClaudeUsageConfig:
    creds_path: str = "data/claude_creds.json"
    poll_interval_seconds: int = 600


@dataclass
class CodexUsageConfig:
    creds_path: str = "data/codex_creds.json"
    poll_interval_seconds: int = 600


@dataclass
class Settings:
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    sensors: SensorsConfig = field(default_factory=SensorsConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    webui: WebUIConfig = field(default_factory=WebUIConfig)
    images: ImagesConfig = field(default_factory=ImagesConfig)
    outdoor_agent: OutdoorAgentConfig = field(default_factory=OutdoorAgentConfig)
    wifi: WifiConfig = field(default_factory=WifiConfig)
    claude_usage: ClaudeUsageConfig = field(default_factory=ClaudeUsageConfig)
    codex_usage: CodexUsageConfig = field(default_factory=CodexUsageConfig)
    timezone: str = "Asia/Taipei"


def _from_dict(cls: type, data: dict):
    if not dataclasses.is_dataclass(cls):
        return data
    hints = get_type_hints(cls)
    kwargs = {}
    for f in dataclasses.fields(cls):
        if f.name not in data:
            continue
        val = data[f.name]
        ftype = hints.get(f.name)
        if ftype is not None and dataclasses.is_dataclass(ftype) and isinstance(val, dict):
            kwargs[f.name] = _from_dict(ftype, val)
        else:
            kwargs[f.name] = val
    return cls(**kwargs)


def _apply_env_overrides(settings: Settings) -> None:
    if os.environ.get("RPI_MOCK") == "1":
        settings.sensors.dht22.use_mock = True
        settings.sensors.light.use_mock = True
        settings.sensors.button.use_mock = True  # gpio_pins remain as-is; mock bypasses GPIO
        settings.display.use_mock = True


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_settings(path: str = "config.yaml") -> Settings:
    raw: dict = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    stem, _ = os.path.splitext(path)
    local_path = stem + ".local.yaml"
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            local_raw = yaml.safe_load(f) or {}
        raw = _deep_merge(raw, local_raw)
    settings = _from_dict(Settings, raw)
    _apply_env_overrides(settings)
    return settings
