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


@dataclass
class WeatherConfig:
    api_key: str = ""
    city_id: int = 1668341
    city_name: str = "Taipei"
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
    gpio_pin: int = 27           # GPIO 17 conflicts with e-Paper RST
    use_mock: bool = False


@dataclass
class SensorsConfig:
    dht22: DHT22Config = field(default_factory=DHT22Config)
    light: LightConfig = field(default_factory=LightConfig)
    button: ButtonConfig = field(default_factory=ButtonConfig)


@dataclass
class DisplayConfig:
    model: str = "epd7in5_V2"
    use_mock: bool = False
    dashboard_trigger_second: int = 57   # render at :SS of each minute
    weather_update_interval: int = 600


@dataclass
class VoiceConfig:
    enabled: bool = True
    player: str = "aplay"
    sounds_dir: str = "assets/sounds"


@dataclass
class DiscordConfig:
    webhook_url: str = ""


@dataclass
class StorageConfig:
    db_path: str = "data/epaper-home-display.db"


@dataclass
class WebUIConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class PresenceConfig:
    light_weight: float = 1.0
    door_weight: float = 1.0
    face_weight: float = 2.0
    threshold: float = 2.0
    door_window_seconds: int = 300
    face_window_seconds: int = 600


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
    timezone: str = "Asia/Taipei"
    presence: PresenceConfig = field(default_factory=PresenceConfig)


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
        settings.sensors.button.use_mock = True
        settings.display.use_mock = True


def load_settings(path: str = "config.yaml") -> Settings:
    raw: dict = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    settings = _from_dict(Settings, raw)
    _apply_env_overrides(settings)
    return settings
