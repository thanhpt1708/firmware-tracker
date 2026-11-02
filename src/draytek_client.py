"""DrayTek crawler and parser for firmware files using httpx."""

import logging
import re
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from packaging.version import InvalidVersion
from packaging.version import parse as parse_version

logger = logging.getLogger(__name__)


@dataclass
class FirmwareInfo:
    """Represents detected firmware details."""

    model_id: str
    model_name: str
    version: str
    version_dir_url: str
    firmware_zip_url: str | None = None
    firmware_zip_name: str | None = None
    firmware_size: str | None = None
    release_note_url: str | None = None
    release_date: str | None = None
    brand: str = "draytek"
    changelog: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DrayTekClient:
    """Client to inspect DrayTek firmware directories via HTTP/2."""

    def __init__(self, timeout: float = 15.0, client: httpx.Client | None = None):
        self.timeout = timeout
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/156.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            ),
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        self.client = client or httpx.Client(
            timeout=self.timeout,
            http2=True,
            follow_redirects=True,
            headers=headers,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self.client.close()

    def __enter__(self) -> DrayTekClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def get_latest_firmware(self, model_id: str, model_name: str, base_url: str) -> FirmwareInfo | None:
        """Find the latest firmware release for a given model."""
        if not base_url.endswith("/"):
            base_url += "/"

        latest_ver = self._fetch_latest_from_txt(base_url)
        if not latest_ver:
            logger.info("latest.txt not found or invalid for %s, falling back to directory parse", model_id)
            latest_ver = self._fetch_latest_from_directory(base_url)

        if not latest_ver:
            logger.warning("Could not determine latest version for %s at %s", model_id, base_url)
            return None

        # Clean version string
        clean_ver = latest_ver.strip().lstrip("vV")

        # Find version directory URL
        version_dir_url = self._resolve_version_dir(base_url, clean_ver)
        if not version_dir_url:
            # Fallback to direct guess
            version_dir_url = f"{base_url}v{clean_ver}/"

        # Inspect version directory for zip & pdf files
        info = self._inspect_version_directory(model_id, model_name, clean_ver, version_dir_url)
        return info

    def _fetch_latest_from_txt(self, base_url: str) -> str | None:
        """Attempt to read version from latest.txt."""
        latest_txt_url = urljoin(base_url, "latest.txt")
        try:
            resp = self.client.get(latest_txt_url)
            if resp.status_code == 200:
                text = resp.text.strip()
                if re.match(r"^v?\d+(\.\d+)+", text):
                    match = re.search(r"v?\d+(\.\d+)+[a-zA-Z0-9_\.]*", text)
                    if match:
                        return match.group(0).strip()
        except httpx.HTTPError as e:
            logger.debug("Failed to fetch latest.txt from %s: %s", latest_txt_url, e)
        return None

    def _fetch_latest_from_directory(self, base_url: str) -> str | None:
        """Parse Apache directory index to find highest version folder."""
        try:
            resp = self.client.get(base_url)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "html.parser")
            versions: list[str] = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                match = re.match(r"^v?(\d+(\.\d+)+[a-zA-Z0-9_\.]*)/?$", href)
                if match:
                    versions.append(match.group(1))

            if not versions:
                return None

            def version_key(v: str):
                try:
                    return parse_version(v.lstrip("vV"))
                except InvalidVersion:
                    return parse_version("0.0.0")

            versions.sort(key=version_key, reverse=True)
            return versions[0]
        except httpx.HTTPError as e:
            logger.error("Error reading directory %s: %s", base_url, e)
            return None

    def _resolve_version_dir(self, base_url: str, version: str) -> str | None:
        """Confirm whether the version directory is v<version>/ or <version>/."""
        candidates = [f"v{version}/", f"{version}/"]
        for cand in candidates:
            cand_url = urljoin(base_url, cand)
            try:
                resp = self.client.head(cand_url)
                if resp.status_code in (200, 301, 302):
                    return cand_url
            except httpx.HTTPError:
                pass
        return urljoin(base_url, f"v{version}/")

    def _inspect_version_directory(
        self, model_id: str, model_name: str, version: str, version_dir_url: str
    ) -> FirmwareInfo:
        """Parse directory contents to find zip, release note, date, and size."""
        info = FirmwareInfo(
            model_id=model_id,
            model_name=model_name,
            version=version,
            version_dir_url=version_dir_url,
        )

        try:
            resp = self.client.get(version_dir_url)
            if resp.status_code != 200:
                return info

            soup = BeautifulSoup(resp.text, "html.parser")
            table = soup.find("table")
            if not table:
                return info

            for tr in table.find_all("tr"):
                cols = tr.find_all(["td", "th"])
                if not cols:
                    continue

                link_elem = tr.find("a", href=True)
                if not link_elem:
                    continue

                href = link_elem["href"].strip()
                href_lower = href.lower()

                row_text = [col.get_text(strip=True) for col in cols]
                col_date = None
                col_size = None
                for col_val in row_text:
                    if re.match(r"^\d{4}-\d{2}-\d{2}", col_val):
                        col_date = col_val
                    elif re.match(r"^\d+(\.\d+)?\s*[KkMmGg]?$", col_val):
                        col_size = col_val

                if href_lower.endswith(".zip"):
                    info.firmware_zip_name = href
                    info.firmware_zip_url = urljoin(version_dir_url, href)
                    if col_size:
                        info.firmware_size = col_size
                    if col_date and not info.release_date:
                        info.release_date = col_date

                elif href_lower.endswith(".pdf"):
                    info.release_note_url = urljoin(version_dir_url, href)
                    if col_date and not info.release_date:
                        info.release_date = col_date

        except httpx.HTTPError as e:
            logger.warning("Failed to inspect version directory %s: %s", version_dir_url, e)

        return info
