"""Unit tests for Telegram notifier using pytest-httpx."""

import json

from pytest_httpx import HTTPXMock

from src.draytek_client import FirmwareInfo
from src.notifier import TelegramNotifier


def test_telegram_notifier_is_configured():
    assert TelegramNotifier(None, None).is_configured() is False
    assert TelegramNotifier("token", "").is_configured() is False
    assert TelegramNotifier("", "12345").is_configured() is False
    assert TelegramNotifier("  token  ", "  12345  ").is_configured() is True


def test_send_message_success(httpx_mock: HTTPXMock):
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    chat_id = "987654321"

    httpx_mock.add_response(
        url=f"https://api.telegram.org/bot{bot_token}/sendMessage",
        method="POST",
        json={"ok": True, "result": {"message_id": 100}},
        status_code=200,
    )

    notifier = TelegramNotifier(bot_token, chat_id)
    result = notifier.send_message("<b>Hello</b>")
    assert result is True

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    req_body = json.loads(requests[0].content)
    assert req_body["chat_id"] == chat_id
    assert req_body["text"] == "<b>Hello</b>"
    assert req_body["parse_mode"] == "HTML"


def test_send_firmware_alert(httpx_mock: HTTPXMock):
    bot_token = "123456:ABC"
    chat_id = "987654"

    httpx_mock.add_response(
        url=f"https://api.telegram.org/bot{bot_token}/sendMessage",
        method="POST",
        json={"ok": True},
        status_code=200,
    )

    notifier = TelegramNotifier(bot_token, chat_id)
    info = FirmwareInfo(
        model_id="vigor2926",
        model_name="DrayTek Vigor 2926 & 2926Ln",
        version="3.9.9.13",
        version_dir_url="https://fw.draytek.com.tw/Vigor2926/Firmware/v3.9.9.13/",
        firmware_zip_name="Vigor2926_v3.9.9.13.zip",
        firmware_zip_url="https://fw.draytek.com.tw/Vigor2926/Firmware/v3.9.9.13/Vigor2926_v3.9.9.13.zip",
        firmware_size="32M",
        release_note_url="https://fw.draytek.com.tw/Vigor2926/Firmware/v3.9.9.13/release-note.pdf",
        release_date="2026-09-30 09:41",
    )

    success = notifier.send_firmware_alert(info)
    assert success is True

    requests = httpx_mock.get_requests()
    req_body = json.loads(requests[0].content)
    text = req_body["text"]
    assert "DrayTek Vigor 2926 &amp; 2926Ln" in text
    assert "<code>v3.9.9.13</code>" in text
    assert "2026-09-30 09:41" in text
    assert "Vigor2926_v3.9.9.13.zip (32M)" in text
    assert "https://fw.draytek.com.tw/Vigor2926/Firmware/v3.9.9.13/release-note.pdf" in text


def test_send_firmware_alert_hikvision(httpx_mock: HTTPXMock):
    bot_token = "123456:ABC"
    chat_id = "987654"

    httpx_mock.add_response(
        url=f"https://api.telegram.org/bot{bot_token}/sendMessage",
        method="POST",
        json={"ok": True},
        status_code=200,
    )

    notifier = TelegramNotifier(bot_token, chat_id)
    info = FirmwareInfo(
        model_id="7208hqhi-m1-e",
        model_name="Hikvision iDS-7208HQHI-M1/E",
        version="4.84.011",
        version_dir_url="https://www.hikvision.com/en/products/.../ids-7208hqhi-m1-e/",
        firmware_zip_name="Firmware_Asia_V4.84.011_251217_S3000693361.zip",
        firmware_zip_url="https://assets.hikvision.com/prd/.../Firmware_Asia.zip",
        firmware_size="31.8M",
        release_note_url="https://assets.hikvision.com/prd/.../Release_Notes.pdf",
        release_date="2025-12-17",
        brand="hikvision",
    )

    success = notifier.send_firmware_alert(info)
    assert success is True

    requests = httpx_mock.get_requests()
    req_body = json.loads(requests[0].content)
    text = req_body["text"]
    assert "CẬP NHẬT FIRMWARE HIKVISION MỚI" in text
    assert "Hikvision iDS-7208HQHI-M1/E" in text
    assert "<code>v4.84.011</code>" in text
    assert "2025-12-17" in text
    assert "Xem Trang Sản Phẩm Hikvision" in text


def test_send_test_message(httpx_mock: HTTPXMock):
    bot_token = "123456:ABC"
    chat_id = "987654"

    httpx_mock.add_response(
        url=f"https://api.telegram.org/bot{bot_token}/sendMessage",
        method="POST",
        json={"ok": True},
        status_code=200,
    )

    notifier = TelegramNotifier(bot_token, chat_id)
    assert notifier.send_test_message() is True

    requests = httpx_mock.get_requests()
    req_body = json.loads(requests[0].content)
    assert "Firmware Release Tracker - Test Notification" in req_body["text"]
