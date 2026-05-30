from __future__ import annotations

import os
import threading

import yaml

_LOCAL_CFG = "config.local.yaml"
_config_lock = threading.Lock()


def _save_to_config(updates: dict) -> None:
    """Atomically deep-merge *updates* into config.local.yaml (thread-safe)."""
    with _config_lock:
        local_raw: dict = {}
        if os.path.exists(_LOCAL_CFG):
            with open(_LOCAL_CFG, "r", encoding="utf-8") as f:
                local_raw = yaml.safe_load(f) or {}
            if not isinstance(local_raw, dict):
                local_raw = {}

        def _merge(base: dict, patch: dict) -> None:
            for k, v in patch.items():
                if isinstance(v, dict) and isinstance(base.get(k), dict):
                    _merge(base[k], v)
                else:
                    base[k] = v

        _merge(local_raw, updates)
        tmp = _LOCAL_CFG + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            yaml.dump(local_raw, f, default_flow_style=False, sort_keys=False)
        os.replace(tmp, _LOCAL_CFG)
