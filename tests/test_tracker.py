"""Unit and integration tests for tracker orchestrator."""

import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest
import yaml

from src.draytek_client import FirmwareInfo
from src.tracker import app, load_config, run_tracker
from typer.testing import CliRunner

runner = CliRunner()


def test_load_config():
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(
            {
                "models": [
                    {"id": "m1", "name": "Model 1", "url": "https://test/m1/", "enabled": True},
                    {"id": "m2", "name": "Model 2", "url": "https://test/m2/", "enabled": False},
                ]
            },
            f,
        )
        temp_path = f.name

    try:
        models = load_config(temp_path)
        assert len(models) == 1
        assert models[0].id == "m1"
    finally:
        os.remove(temp_path)


@patch("src.tracker.TelegramNotifier")
@patch("src.tracker.DrayTekClient")
def test_run_tracker_new_version_flow(mock_client_cls, mock_notifier_cls):
    mock_client = MagicMock()
    mock_notifier = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_notifier_cls.return_value = mock_notifier

    mock_client.get_latest_firmware.return_value = FirmwareInfo(
        model_id="vigor2926",
        model_name="Vigor 2926",
        version="3.9.9.13",
        version_dir_url="https://fw.draytek.com.tw/Vigor2926/Firmware/v3.9.9.13/",
        firmware_zip_name="Vigor2926_v3.9.9.13.zip",
        firmware_zip_url="https://fw.draytek.com.tw/Vigor2926/Firmware/v3.9.9.13/Vigor2926_v3.9.9.13.zip",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, "models.yaml")
        state_file = os.path.join(tmpdir, "state.json")

        with open(config_file, "w") as f:
            yaml.dump(
                {
                    "models": [
                        {
                            "id": "vigor2926",
                            "name": "Vigor 2926",
                            "url": "https://fw.draytek.com.tw/Vigor2926/Firmware/",
                            "enabled": True,
                        }
                    ]
                },
                f,
            )

        # First run with notify_on_init=True
        exit_code = run_tracker(
            config_path=config_file,
            state_path=state_file,
            dry_run=False,
            notify_on_init=True,
        )
        assert exit_code == 0
        mock_notifier.send_firmware_alert.assert_called_once()

        # Second run with same version -> No notification
        mock_notifier.reset_mock()
        exit_code = run_tracker(
            config_path=config_file,
            state_path=state_file,
            dry_run=False,
            notify_on_init=True,
        )
        assert exit_code == 0
        mock_notifier.send_firmware_alert.assert_not_called()


@patch("src.tracker.run_tracker")
def test_cli_check_command(mock_run_tracker):
    mock_run_tracker.return_value = 0
    result = runner.invoke(app, ["check", "--dry-run", "--model", "vigor2926"])
    assert result.exit_code == 0
    mock_run_tracker.assert_called_once_with(
        config_path="config/models.yaml",
        state_path="data/state.json",
        dry_run=True,
        force_notify=False,
        notify_on_init=True,
        target_model="vigor2926",
    )


@patch("src.tracker.TelegramNotifier")
def test_cli_test_telegram_command(mock_notifier_cls):
    mock_notifier = MagicMock()
    mock_notifier_cls.return_value = mock_notifier
    mock_notifier.is_configured.return_value = True
    mock_notifier.send_test_message.return_value = True

    result = runner.invoke(app, ["test-telegram"])
    assert result.exit_code == 0
    mock_notifier.send_test_message.assert_called_once()
