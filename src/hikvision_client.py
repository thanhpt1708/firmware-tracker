"""Hikvision crawler and parser for firmware files using httpx."""

import logging
import re
from typing import Any, Self
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from src.draytek_client import FirmwareInfo

logger = logging.getLogger(__name__)


def format_file_size(bytes_size: int) -> str:
    """Format byte size into human readable string (e.g. 31.8M)."""
    if bytes_size >= 1024 * 1024 * 1024:
        return f"{bytes_size / (1024**3):.1f}G"
    if bytes_size >= 1024 * 1024:
        return f"{bytes_size / (1024**2):.1f}M"
    if bytes_size >= 1024:
        return f"{bytes_size / 1024:.0f}K"
    return f"{bytes_size}B"


class HikvisionClient:
    """Client to scrape and parse Hikvision firmware releases."""

    DEFAULT_CATALOG_URL = "https://www.hikvision.com/en/support/download/firmware/"

    def __init__(self, timeout: float = 30.0, client: httpx.Client | None = None):
        self.timeout = timeout
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.client = client or httpx.Client(
            timeout=self.timeout,
            http2=True,
            follow_redirects=True,
            headers=headers,
        )
        self._cached_catalog_html: str | None = None

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self.client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def fetch_catalog(self, catalog_url: str = DEFAULT_CATALOG_URL) -> str | None:
        """Fetch the full firmware catalog HTML (caches in-memory during session)."""
        if self._cached_catalog_html is not None:
            return self._cached_catalog_html

        try:
            logger.info("Fetching Hikvision firmware catalog from %s...", catalog_url)
            resp = self.client.get(catalog_url)
            if resp.status_code == 200 and len(resp.text) > 1000:
                self._cached_catalog_html = resp.text
                logger.info(
                    "Hikvision catalog loaded successfully (%.2f MB).",
                    len(resp.text) / (1024 * 1024),
                )
                return self._cached_catalog_html
            logger.error("Failed to fetch catalog: HTTP %d (Length: %d)", resp.status_code, len(resp.text))
        except httpx.HTTPError as e:
            logger.error("HTTP error while fetching Hikvision catalog: %s", e)
        return None

    def find_model_block(self, html: str, target: str) -> str | None:
        """Find and extract the enclosing HTML block for a given model target."""
        clean_target = target.lower().strip()
        variants = [
            clean_target,
            clean_target.replace("/", "-"),
            clean_target.replace("-", "").replace("/", ""),
        ]
        if not clean_target.startswith(("ids-", "ds-", "ids", "ds")):
            variants.extend([
                f"ids-{clean_target.replace('/', '-')}",
                f"ds-{clean_target.replace('/', '-')}",
            ])

        idx = -1
        html_lower = html.lower()
        for variant in variants:
            found_pos = html_lower.find(variant)
            if found_pos != -1:
                idx = found_pos
                logger.debug("Found model match with variant '%s' at offset %d", variant, idx)
                break

        if idx == -1:
            return None

        start_tag = '<div class="nav-item'
        start_idx = html.rfind(start_tag, 0, idx)
        if start_idx == -1:
            start_idx = 0

        next_idx = html.find(start_tag, idx + 10)
        if next_idx == -1:
            next_idx = len(html)

        return html[start_idx:next_idx]

    def parse_model_block(
        self,
        block_html: str,
        model_id: str,
        model_name: str,
        region: str = "Asia",
    ) -> FirmwareInfo | None:
        """Parse model block to extract latest firmware, release notes, and download links."""
        soup = BeautifulSoup(block_html, "html.parser")
        main_link = soup.find("a", class_="link")
        product_title = main_link.text.strip() if main_link else model_name
        product_path = main_link["href"] if main_link and "href" in main_link.attrs else ""
        product_url = urljoin("https://www.hikvision.com", product_path) if product_path else self.DEFAULT_CATALOG_URL

        # Extract all firmware download links
        firmware_elems = soup.select(".firmware-asstes a.assets")
        if not firmware_elems:
            logger.warning("No firmware assets found in block for %s", model_id)
            return None

        firmwares: list[dict[str, str]] = []
        for elem in firmware_elems:
            title = elem.get("data-title") or elem.text.strip()
            href = elem.get("data-href") or elem.get("data-link") or elem.get("href") or ""
            if href:
                firmwares.append({"title": title, "url": href})

        if not firmwares:
            return None

        # Select the preferred regional firmware (e.g. Asia vs Europe)
        chosen_fw = firmwares[0]
        region_clean = region.lower().strip()
        for fw in firmwares:
            if region_clean in fw["title"].lower():
                chosen_fw = fw
                break

        fw_url = chosen_fw["url"]
        fw_title = chosen_fw["title"]
        fw_zip_name = fw_url.split("/")[-1].split("?")[0]

        # Extract version
        version = "Unknown"
        ver_match = re.search(r"[vV](\d+(?:\.\d+)+)", fw_title) or re.search(r"[vV](\d+(?:\.\d+)+)", fw_zip_name)
        if ver_match:
            version = ver_match.group(1)

        # Extract build date if present (e.g. 251217 -> 2025-12-17)
        release_date = None
        build_match = re.search(r"build[_\s]?(\d{6})|_(\d{6})(?:_|\.|$)", fw_title, re.IGNORECASE) or re.search(
            r"_(\d{6})_", fw_zip_name
        )
        if build_match:
            b_str = build_match.group(1) or build_match.group(2)
            try:
                year = 2000 + int(b_str[:2])
                month = b_str[2:4]
                day = b_str[4:6]
                release_date = f"{year}-{month}-{day}"
            except ValueError:
                logger.debug("Failed to parse date from build string '%s'", b_str)

        # Extract release notes PDF
        rn_elem = soup.select_one(".release-asstes a.assets")
        rn_url = None
        if rn_elem:
            rn_url = rn_elem.get("data-href") or rn_elem.get("data-link") or rn_elem.get("href")

        # Query file size and Last-Modified via HEAD request
        firmware_size = None
        try:
            head_resp = self.client.head(
                fw_url,
                headers={"Referer": self.DEFAULT_CATALOG_URL},
                timeout=10.0,
            )
            if head_resp.status_code == 200:
                content_len = head_resp.headers.get("content-length")
                if content_len and content_len.isdigit():
                    firmware_size = format_file_size(int(content_len))

                if not release_date:
                    last_mod = head_resp.headers.get("last-modified")
                    if last_mod:
                        release_date = last_mod
        except httpx.HTTPError as e:
            logger.debug("Failed HEAD request on firmware asset %s: %s", fw_url, e)

        return FirmwareInfo(
            model_id=model_id,
            model_name=product_title if product_title != "Unknown" else model_name,
            version=version,
            version_dir_url=product_url,
            firmware_zip_url=fw_url,
            firmware_zip_name=fw_zip_name,
            firmware_size=firmware_size,
            release_note_url=rn_url,
            release_date=release_date,
            brand="hikvision",
        )

    def get_latest_firmware(
        self,
        model_id: str,
        model_name: str,
        catalog_url: str = DEFAULT_CATALOG_URL,
        region: str = "Asia",
        model_name_match: str | None = None,
    ) -> FirmwareInfo | None:
        """Find the latest firmware release for a given Hikvision model."""
        html = self.fetch_catalog(catalog_url)
        if not html:
            logger.warning("Could not obtain Hikvision catalog HTML")
            return None

        search_query = model_name_match or model_id
        block = self.find_model_block(html, search_query)
        if not block:
            logger.warning("Model block not found for '%s' in Hikvision catalog", search_query)
            return None

        return self.parse_model_block(
            block_html=block,
            model_id=model_id,
            model_name=model_name,
            region=region,
        )
