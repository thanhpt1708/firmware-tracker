"""Main tracker orchestrator for firmware releases (DrayTek, Hikvision...)."""

import logging
import os
from datetime import UTC, datetime

import typer
from dotenv import load_dotenv

from src.config import ModelConfig, TrackerConfig
from src.draytek_client import DrayTekClient
from src.hikvision_client import HikvisionClient
from src.notifier import TelegramNotifier
from src.state_manager import StateManager, is_new_or_different
from src.tplink_client import TPLinkClient

# Load environment variables from .env file if available
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Keep third-party libraries quiet by default
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger("tracker")

app = typer.Typer(
    help="🛰️ Firmware Release Tracker & Telegram Notifier CLI",
    no_args_is_help=False,
)


def load_config(config_path: str = "config/models.yaml") -> list[ModelConfig]:
    """Load and validate list of models from YAML config using Pydantic."""
    if not os.path.exists(config_path):
        logger.error("Configuration file not found: %s", config_path)
        raise typer.Exit(code=1)

    try:
        config = TrackerConfig.from_yaml(config_path)
        return config.get_enabled_models()
    except Exception as e:
        logger.error("Failed to parse configuration file %s: %s", config_path, e)
        raise typer.Exit(code=1)


def run_tracker(
    config_path: str = "config/models.yaml",
    state_path: str = "data/state.json",
    dry_run: bool = False,
    force_notify: bool = False,
    notify_on_init: bool = True,
    target_model: str = "",
    target_brand: str = "",
) -> int:
    """Run tracking loop across all configured models."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
    draytek_client = DrayTekClient()
    hikvision_client = HikvisionClient()
    tplink_client = TPLinkClient()
    state_mgr = StateManager(state_path)
    state = state_mgr.load()

    models = load_config(config_path)
    if target_brand:
        models = [m for m in models if m.brand.lower() == target_brand.lower()]
        if not models:
            logger.error("No enabled models found for brand '%s' in %s", target_brand, config_path)
            return 1

    if target_model:
        models = [m for m in models if m.id == target_model]
        if not models:
            logger.error("Model ID '%s' not found or not enabled in %s", target_model, config_path)
            return 1

    logger.info("Starting check for %d model(s)...", len(models))
    state_changed = False

    try:
        for model in models:
            model_id = model.id
            model_name = model.name
            url = model.url
            brand = model.brand.lower()

            match brand:
                case "hikvision":
                    logger.info("Checking Hikvision '%s' (%s)...", model_name, model_id)
                    info = hikvision_client.get_latest_firmware(
                        model_id=model_id,
                        model_name=model_name,
                        catalog_url=url,
                        region=model.region,
                        model_name_match=model.model_name_match,
                    )
                case "tplink":
                    logger.info("Checking TP-Link '%s' (%s) at %s...", model_name, model_id, url)
                    info = tplink_client.get_latest_firmware(
                        model_id=model_id,
                        model_name=model_name,
                        url=url,
                        hw_version=model.hw_version,
                    )
                case "draytek" | _:
                    logger.info("Checking DrayTek '%s' (%s) at %s...", model_name, model_id, url)
                    info = draytek_client.get_latest_firmware(model_id=model_id, model_name=model_name, base_url=url)

            if not info:
                logger.warning("Could not fetch firmware information for %s", model_id)
                continue

            current_record = state_mgr.get_model(state, model_id)
            current_version = current_record.get("version") if current_record else None

            is_new_model = current_record is None
            is_newer = is_new_or_different(current_version, info.version)

            logger.info(
                "[%s] Detected version: %s | Known version: %s",
                model_id,
                info.version,
                current_version or "None",
            )

            should_notify = force_notify or (is_new_model and notify_on_init) or (not is_new_model and is_newer)

            if should_notify:
                logger.info("Sending alert for %s (v%s)...", model_name, info.version)
                if dry_run:
                    logger.info("[DRY RUN] Notification skipped.")
                else:
                    sent = notifier.send_firmware_alert(info)
                    if not sent and notifier.is_configured():
                        logger.warning("Failed to send notification via Telegram.")

            if is_new_model or is_newer or force_notify:
                state_record = info.to_dict()
                state_record["last_checked"] = datetime.now(UTC).isoformat()
                state_mgr.update_model(state, model_id, state_record)
                state_changed = True
            else:
                logger.info("[%s] Firmware v%s is already up to date.", model_id, info.version)
                if current_record:
                    current_record["last_checked"] = datetime.now(UTC).isoformat()
                    state_changed = True

        if state_changed:
            if dry_run:
                logger.info("[DRY RUN] State changes not saved.")
            else:
                state_mgr.save(state)
                logger.info("State successfully saved to %s", state_path)
    finally:
        draytek_client.close()
        hikvision_client.close()
        tplink_client.close()

    logger.info("Firmware check completed.")
    return 0


@app.command("check")
def check_command(
    config: str = typer.Option("config/models.yaml", "--config", "-c", help="Path to models YAML config"),
    state: str = typer.Option("data/state.json", "--state", "-s", help="Path to state JSON file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Crawl without sending alert or saving state"),
    force_notify: bool = typer.Option(False, "--force-notify", help="Always send notification regardless of state"),
    notify_on_init: bool = typer.Option(
        os.environ.get("NOTIFY_ON_INIT", "true").lower() in ("true", "1", "yes"),
        "--notify-on-init/--no-notify-on-init",
        help="Send notification on first run for newly tracked models",
    ),
    model: str = typer.Option("", "--model", "-m", help="Only check a specific model ID"),
    brand: str = typer.Option("", "--brand", "-b", help="Only check models from a specific brand (e.g. draytek, hikvision, tplink)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging"),
) -> None:
    """Check firmware releases and notify via Telegram if a new version is found."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("httpx").setLevel(logging.DEBUG)
        logging.getLogger("httpcore").setLevel(logging.DEBUG)

    exit_code = run_tracker(
        config_path=config,
        state_path=state,
        dry_run=dry_run,
        force_notify=force_notify,
        notify_on_init=notify_on_init,
        target_model=model,
        target_brand=brand,
    )
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@app.command("test-telegram")
def test_telegram_command() -> None:
    """Send a test message to Telegram to verify credentials."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)

    if not notifier.is_configured():
        logger.error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in environment or .env file.")
        raise typer.Exit(code=1)

    logger.info("Sending test message to Telegram...")
    success = notifier.send_test_message()
    if not success:
        logger.error("Failed to send test message. Check bot token and chat ID.")
        raise typer.Exit(code=1)
    logger.info("Test message sent successfully!")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    config: str = typer.Option("config/models.yaml", "--config", "-c", help="Path to models YAML config"),
    state: str = typer.Option("data/state.json", "--state", "-s", help="Path to state JSON file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Crawl without sending alert or saving state"),
    force_notify: bool = typer.Option(False, "--force-notify", help="Always send notification regardless of state"),
    notify_on_init: bool = typer.Option(
        os.environ.get("NOTIFY_ON_INIT", "true").lower() in ("true", "1", "yes"),
        "--notify-on-init/--no-notify-on-init",
        help="Send notification on first run for newly tracked models",
    ),
    model: str = typer.Option("", "--model", "-m", help="Only check a specific model ID"),
    brand: str = typer.Option("", "--brand", "-b", help="Only check models from a specific brand (e.g. draytek, hikvision, tplink)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging"),
) -> None:
    """🛰️ Firmware Tracker CLI."""
    if ctx.invoked_subcommand is None:
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.getLogger("httpx").setLevel(logging.DEBUG)
            logging.getLogger("httpcore").setLevel(logging.DEBUG)
        exit_code = run_tracker(
            config_path=config,
            state_path=state,
            dry_run=dry_run,
            force_notify=force_notify,
            notify_on_init=notify_on_init,
            target_model=model,
            target_brand=brand,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
