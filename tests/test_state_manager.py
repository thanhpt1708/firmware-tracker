"""Unit tests for state manager and packaging version comparison."""

import os
import tempfile
import pytest

from src.state_manager import StateManager, is_new_or_different


def test_is_new_or_different():
    # Brand new model
    assert is_new_or_different(None, "3.9.9.13") is True

    # Same version
    assert is_new_or_different("3.9.9.13", "3.9.9.13") is False
    assert is_new_or_different("v3.9.9.13", "3.9.9.13") is False
    assert is_new_or_different("3.9.9.13", "v3.9.9.13") is False

    # Newer version
    assert is_new_or_different("3.9.9.2", "3.9.9.13") is True
    assert is_new_or_different("3.9.9.12", "3.9.9.13") is True
    assert is_new_or_different("3.9.8", "3.9.9") is True
    assert is_new_or_different("3.9.9.13", "4.0.0") is True
    assert is_new_or_different("4.0.0a1", "4.0.0") is True

    # Older version
    assert is_new_or_different("3.9.9.13", "3.9.9.2") is False


def test_state_manager_load_and_save():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, "state.json")
        mgr = StateManager(state_file)

        # Loading empty/non-existent
        assert mgr.load() == {}

        # Save and reload
        sample_state = {
            "vigor2926": {
                "version": "3.9.9.13",
                "firmware_size": "32M",
            }
        }
        mgr.save(sample_state)

        loaded = mgr.load()
        assert loaded == sample_state
        assert mgr.get_model(loaded, "vigor2926")["version"] == "3.9.9.13"
        assert mgr.get_model(loaded, "nonexistent") is None

        # Update model
        mgr.update_model(loaded, "vigor2962", {"version": "4.4.6.3"})
        mgr.save(loaded)

        reloaded = mgr.load()
        assert "vigor2962" in reloaded
        assert reloaded["vigor2962"]["version"] == "4.4.6.3"
