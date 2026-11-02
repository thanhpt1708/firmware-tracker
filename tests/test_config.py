"""Unit tests for Pydantic configuration models."""

import pytest
from pydantic import ValidationError

from src.config import ModelConfig, TrackerConfig


def test_model_config_valid():
    model = ModelConfig(
        id="vigor2926",
        name="Vigor 2926",
        url="https://fw.draytek.com.tw/Vigor2926/Firmware/",
    )
    assert model.id == "vigor2926"
    assert model.enabled is True


def test_model_config_missing_required():
    with pytest.raises(ValidationError):
        ModelConfig(id="vigor2926")  # Missing name and url


def test_tracker_config_filter_enabled():
    config = TrackerConfig(
        models=[
            ModelConfig(id="m1", name="Model 1", url="https://m1/", enabled=True),
            ModelConfig(id="m2", name="Model 2", url="https://m2/", enabled=False),
        ]
    )
    enabled = config.get_enabled_models()
    assert len(enabled) == 1
    assert enabled[0].id == "m1"


def test_tracker_config_vendor_sections():
    raw = {
        "draytek": [
            {"id": "v2926", "name": "Vigor 2926", "url": "https://fw.draytek.com/v2926/", "enabled": True},
            {"id": "v2927", "name": "Vigor 2927", "url": "https://fw.draytek.com/v2927/", "enabled": False},
        ],
        "hikvision": [
            {"id": "7208hqhi-m1-e", "name": "iDS-7208HQHI-M1/E", "enabled": True},
        ],
    }
    config = TrackerConfig.model_validate(raw)
    all_models = config.get_all_models()
    assert len(all_models) == 3

    enabled = config.get_enabled_models()
    assert len(enabled) == 2
    assert enabled[0].brand == "draytek"
    assert enabled[1].brand == "hikvision"
    assert enabled[1].url == "https://www.hikvision.com/en/support/download/firmware/"
