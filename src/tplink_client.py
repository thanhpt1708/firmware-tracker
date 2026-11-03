"""TP-Link and Deco crawler and parser for firmware files using httpx."""

import logging
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from src.draytek_client import FirmwareInfo
from src.http_client import BaseCrawlerClient

logger = logging.getLogger(__name__)


def extract_tplink_version(raw_name: str) -> str:
    """Extract clean version string from TP-Link firmware title.

    Examples:
        'Deco M4(EU)_V1_1.8.2 Build 20251027' -> '1.8.2 Build 20251027'
        'Archer AX55(EU)_V4_251030' -> '251030'
        'Archer C6(US)_V3.20_210716' -> '210716'
        'Deco X20(US)_V1_1.5.1 Build 20210204 Rel. 50164' -> '1.5.1 Build 20210204'
        'TL-WR841N(EU)_V14_180319' -> '180319'
    """
    # Remove region like (EU), (US), (UN), etc.
    clean = re.sub(r"\(.*?\)", "", raw_name)
    # Remove hardware version token like _V1_, _V3.20_, _V2_
    clean = re.sub(r"_V\d+(?:\.\d+)?_?", " ", clean, flags=re.I)

    # 1. Match semantic version with optional Build number
    m = re.search(r"(\d+\.\d+(?:\.\d+)*(?:\s*(?:Build|rel\.|_Build_)\s*\d+)?)", clean, re.I)
    if m:
        return m.group(1).strip()

    # 2. Match build date YYMMDD or YYYYMMDD
    m = re.search(r"(\d{6,8})", clean)
    if m:
        return m.group(1).strip()

    return raw_name.strip()


class TPLinkClient(BaseCrawlerClient):
    """Client to scrape and parse TP-Link / Deco firmware download pages."""

    def __init__(self, timeout: float = 20.0, client: httpx.Client | None = None) -> None:
        super().__init__(timeout=timeout, client=client)

    def build_target_url(self, base_url: str, hw_version: str | None = None) -> str:
        """Ensure correct URL including optional hardware version subpath."""
        url = base_url.strip()
        if not url.endswith("/"):
            url += "/"

        if hw_version:
            hw_norm = hw_version.strip().lower()
            if not hw_norm.startswith("v"):
                hw_norm = f"v{hw_norm}"
            # Avoid appending duplicate hw_version if already in url
            if not url.rstrip("/").endswith(f"/{hw_norm}"):
                url = urljoin(url, f"{hw_norm}/")

        return url

    def get_latest_firmware(
        self,
        model_id: str,
        model_name: str,
        url: str,
        hw_version: str | None = None,
    ) -> FirmwareInfo | None:
        """Fetch and parse download page for the latest firmware release."""
        target_url = self.build_target_url(url, hw_version)
        logger.info("Fetching TP-Link firmware page from: %s", target_url)

        try:
            resp = self.client.get(target_url)
            if resp.status_code != 200:
                logger.error("Failed to fetch TP-Link page %s (HTTP %s)", target_url, resp.status_code)
                return None
            html_text = resp.text
        except httpx.HTTPError as e:
            logger.error("HTTP error fetching TP-Link page %s: %s", target_url, e)
            return None

        return self.parse_download_page(
            html_text=html_text,
            page_url=str(resp.url),
            model_id=model_id,
            model_name=model_name,
        )

    def parse_download_page(
        self,
        html_text: str,
        page_url: str,
        model_id: str,
        model_name: str,
    ) -> FirmwareInfo | None:
        """Parse HTML download page to extract the top-most firmware entry."""
        soup = BeautifulSoup(html_text, "html.parser")

        # Find the primary firmware table
        # TP-Link download tables have class 'download-resource-table'
        tables = soup.find_all("table", class_="download-resource-table")
        if not tables:
            logger.warning("No firmware tables found at %s", page_url)
            return None

        # The first table on the page represents the latest released firmware
        latest_table = tables[0]

        # 1. Raw firmware title/name
        name_el = latest_table.select_one(".download-resource-name p, .download-resource-name")
        raw_name = name_el.get_text(strip=True) if name_el else ""
        if not raw_name:
            logger.warning("Could not find firmware name in top table at %s", page_url)
            return None

        version = extract_tplink_version(raw_name)

        # 2. Download zip URL
        zip_url: str | None = None
        # Links may be direct in button or inside download modal popup
        for a in latest_table.find_all("a", href=True):
            href = a["href"].strip()
            if ".zip" in href.lower() or "static.tp-link.com" in href.lower():
                zip_url = href
                break

        zip_name: str | None = None
        if zip_url:
            zip_name = zip_url.split("/")[-1]
            if "?" in zip_name:
                zip_name = zip_name.split("?")[0]

        # 3. Published date and file size
        published_date: str | None = None
        file_size: str | None = None

        detail_tds = latest_table.select(".detail-info td")
        for td in detail_tds:
            text = td.get_text(separator=" ", strip=True)
            # Detect published date (e.g. Published Date: 2025-12-12 or Ngày phát hành: ...)
            if any(k in text.lower() for k in ["published date", "release date", "ngày phát hành"]):
                m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
                if m:
                    published_date = m.group(1)

            # Detect file size (e.g. File Size: 13.68 MB or Dung lượng: ...)
            if any(k in text.lower() for k in ["file size", "size", "dung lượng"]):
                m = re.search(r"([\d\.]+\s*(?:[KMG]B|Bytes))", text, re.I)
                if m:
                    file_size = m.group(1)

        # 4. Release notes / Changelog
        changelog: str | None = None
        more_td = latest_table.select_one(".more-info td.more, .more-info")
        if more_td:
            cl_text = more_td.get_text(separator="\n", strip=True)
            # Clean empty lines
            cl_lines = [line.strip() for line in cl_text.splitlines() if line.strip()]
            if cl_lines:
                changelog = "\n".join(cl_lines)

        return FirmwareInfo(
            model_id=model_id,
            model_name=model_name,
            version=version,
            version_dir_url=page_url,
            firmware_zip_url=zip_url,
            firmware_zip_name=zip_name,
            firmware_size=file_size,
            release_note_url=None,
            release_date=published_date,
            brand="tplink",
            changelog=changelog,
        )

