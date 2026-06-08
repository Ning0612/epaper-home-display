"""Unit tests for VoiceService config validation (volume, alsa_mixer_control)."""
from __future__ import annotations

import pytest

from app.config import VoiceConfig
from app.services.voice import VoiceService


def _make_service(**kwargs) -> VoiceService:
    cfg = VoiceConfig(**kwargs)
    return VoiceService(cfg)


class TestVolumeValidation:
    def test_volume_zero_accepted(self):
        svc = _make_service(volume=0)
        assert svc._config.volume == 0

    def test_volume_100_accepted(self):
        svc = _make_service(volume=100)
        assert svc._config.volume == 100

    def test_volume_clamped_above_100(self):
        svc = _make_service(volume=999)
        assert svc._config.volume == 100

    def test_volume_clamped_below_0(self):
        svc = _make_service(volume=-5)
        assert svc._config.volume == 0

    def test_volume_default(self):
        svc = _make_service()
        assert 0 <= svc._config.volume <= 100


class TestAlsaMixerControlValidation:
    def test_pcm_accepted(self):
        svc = _make_service(alsa_mixer_control="PCM")
        assert svc._config.alsa_mixer_control == "PCM"

    def test_master_accepted(self):
        svc = _make_service(alsa_mixer_control="Master")
        assert svc._config.alsa_mixer_control == "Master"

    def test_empty_string_accepted(self):
        svc = _make_service(alsa_mixer_control="")
        assert svc._config.alsa_mixer_control == ""

    def test_whitespace_trimmed_to_empty(self):
        svc = _make_service(alsa_mixer_control="   ")
        assert svc._config.alsa_mixer_control == ""

    def test_hyphen_leading_rejected(self):
        svc = _make_service(alsa_mixer_control="-q")
        assert svc._config.alsa_mixer_control == ""

    def test_semicolon_injection_rejected(self):
        svc = _make_service(alsa_mixer_control=";rm -rf /")
        assert svc._config.alsa_mixer_control == ""

    def test_shell_metachar_rejected(self):
        svc = _make_service(alsa_mixer_control="PCM && echo hi")
        assert svc._config.alsa_mixer_control == ""

    def test_name_with_space_accepted(self):
        svc = _make_service(alsa_mixer_control="Speaker 1")
        assert svc._config.alsa_mixer_control == "Speaker 1"

    def test_name_with_hyphen_inside_accepted(self):
        svc = _make_service(alsa_mixer_control="PCM-Out")
        assert svc._config.alsa_mixer_control == "PCM-Out"
