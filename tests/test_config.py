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

