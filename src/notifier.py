"""Telegram notifier for firmware release alerts using httpx."""

import html
import logging

import httpx

from src.draytek_client import FirmwareInfo

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends notifications to Telegram via Bot API."""

    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        self.bot_token = bot_token.strip() if bot_token else None
        self.chat_id = chat_id.strip() if chat_id else None

    def is_configured(self) -> bool:
        """Check if both bot token and chat id are provided."""
        return bool(self.bot_token and self.chat_id)

    def send_message(self, text: str, disable_web_page_preview: bool = True) -> bool:
        """Send a formatted HTML message to the configured Telegram chat."""
        if not self.is_configured():
            logger.warning("Telegram Bot Token or Chat ID not configured. Skipping notification.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_web_page_preview,
        }

        try:
            resp = httpx.post(url, json=payload, timeout=15.0)
            if resp.status_code == 200:
                logger.info("Successfully sent Telegram notification.")
                return True
            else:
                clean_err = resp.text.replace(self.bot_token, "***") if self.bot_token else resp.text
                logger.error("Failed to send Telegram message: HTTP %s - %s", resp.status_code, clean_err)
                return False
        except httpx.HTTPError as e:
            clean_err = str(e).replace(self.bot_token, "***") if self.bot_token else str(e)
            logger.error("Exception occurred while sending Telegram notification: %s", clean_err)
            return False

    def send_firmware_alert(self, info: FirmwareInfo) -> bool:
        """Format and send firmware alert message."""
        brand_name = info.brand.upper()
        model_name = html.escape(info.model_name)
        ver_str = info.version if info.version.lower().startswith("v") else f"v{info.version}"
        version = html.escape(ver_str)
        release_date = html.escape(info.release_date or "Chưa rõ")

        lines = [
            f"🚀 <b>CẬP NHẬT FIRMWARE {brand_name} MỚI</b>",
            "",
            f"📌 <b>Thiết bị:</b> {model_name}",
            f"🏷 <b>Phiên bản:</b> <code>{version}</code>",
            f"🗓 <b>Ngày phát hành:</b> {release_date}",
            "",
            "🔗 <b>Tài liệu & Tải về:</b>",
        ]

        if info.release_note_url:
            lines.append(f'• 📄 <a href="{info.release_note_url}">Xem Release Notes (PDF)</a>')

        if info.firmware_zip_url:
            size_txt = f" ({info.firmware_size})" if info.firmware_size else ""
            zip_label = html.escape(info.firmware_zip_name or "Firmware ZIP")
            lines.append(f'• 💾 <a href="{info.firmware_zip_url}">Tải {zip_label}{size_txt}</a>')

        match info.brand.lower():
            case "hikvision":
                folder_label = "Xem Trang Sản Phẩm Hikvision"
            case "draytek":
                folder_label = "Mở Thư mục Firmware"
            case _:
                folder_label = "Mở Thư mục Firmware"

        lines.append(f'• 📂 <a href="{info.version_dir_url}">{folder_label}</a>')

        message = "\n".join(lines)
        return self.send_message(message)

    def send_test_message(self) -> bool:
        """Send a test message to verify Telegram bot setup."""
        test_msg = (
            "🤖 <b>Firmware Release Tracker - Test Notification</b>\n\n"
            "✅ Kết nối Telegram Bot thành công!\n"
            "Hệ thống theo dõi firmware đã sẵn sàng hoạt động."
        )
        return self.send_message(test_msg)
