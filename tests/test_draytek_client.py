"""Unit tests for DrayTek client and scraper using pytest-httpx."""

from pytest_httpx import HTTPXMock

from src.draytek_client import DrayTekClient

SAMPLE_ROOT_DIR_HTML = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">
<html>
<head><title>Index of /Vigor2926/Firmware</title></head>
<body>
<h1>Index of /Vigor2926/Firmware</h1>
<table>
<tr><th>Name</th><th>Last modified</th><th>Size</th></tr>
<tr><td><a href="/Vigor2926/">Parent Directory</a></td><td>&nbsp;</td><td>  - </td></tr>
<tr><td><a href="v3.8.5/">v3.8.5/</a></td><td>2017-10-30 09:49  </td><td>  - </td></tr>
<tr><td><a href="v3.9.9.2/">v3.9.9.2/</a></td><td>2023-08-03 15:46  </td><td>  - </td></tr>
<tr><td><a href="v3.9.9.13/">v3.9.9.13/</a></td><td>2026-09-30 09:41  </td><td>  - </td></tr>
</table>
</body>
</html>
"""

SAMPLE_VERSION_DIR_HTML = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">
<html>
<head><title>Index of /Vigor2926/Firmware/v3.9.9.13</title></head>
<body>
<h1>Index of /Vigor2926/Firmware/v3.9.9.13</h1>
<table>
<tr><th>Name</th><th>Last modified</th><th>Size</th></tr>
<tr><td><a href="/Vigor2926/Firmware/">Parent Directory</a></td><td>&nbsp;</td><td>  - </td></tr>
<tr><td><a href="DrayTek_Vigor2926_V3.9.9.13_release-note.pdf">DrayTek_Vigor2926_V3.9.9.13_release-note.pdf</a></td><td>2026-09-30 09:41  </td><td>190K</td></tr>
<tr><td><a href="FIRMWARE.DIGESTS">FIRMWARE.DIGESTS</a></td><td>2026-09-30 09:41  </td><td>373</td></tr>
<tr><td><a href="Vigor2926_v3.9.9.13.zip">Vigor2926_v3.9.9.13.zip</a></td><td>2026-09-30 09:41  </td><td> 32M</td></tr>
</table>
</body>
</html>
"""


def test_get_latest_firmware_via_latest_txt(httpx_mock: HTTPXMock):
    base_url = "https://fw.draytek.com.tw/Vigor2926/Firmware/"

    # 1. latest.txt returns 3.9.9.13
    httpx_mock.add_response(
        url="https://fw.draytek.com.tw/Vigor2926/Firmware/latest.txt",
        text="3.9.9.13\n",
        status_code=200,
    )
    # 2. HEAD on v3.9.9.13/
    httpx_mock.add_response(
        url="https://fw.draytek.com.tw/Vigor2926/Firmware/v3.9.9.13/",
        method="HEAD",
        status_code=200,
    )
    # 3. GET on v3.9.9.13/
    httpx_mock.add_response(
        url="https://fw.draytek.com.tw/Vigor2926/Firmware/v3.9.9.13/",
        method="GET",
        text=SAMPLE_VERSION_DIR_HTML,
        status_code=200,
    )

    with DrayTekClient() as client:
        info = client.get_latest_firmware("vigor2926", "Vigor 2926", base_url)

    assert info is not None
    assert info.model_id == "vigor2926"
    assert info.version == "3.9.9.13"
    assert info.firmware_zip_name == "Vigor2926_v3.9.9.13.zip"
    assert info.firmware_zip_url == "https://fw.draytek.com.tw/Vigor2926/Firmware/v3.9.9.13/Vigor2926_v3.9.9.13.zip"
    assert (
        info.release_note_url
        == "https://fw.draytek.com.tw/Vigor2926/Firmware/v3.9.9.13/DrayTek_Vigor2926_V3.9.9.13_release-note.pdf"
    )
    assert info.firmware_size == "32M"
    assert info.release_date == "2026-09-30 09:41"


def test_fallback_to_directory_when_latest_txt_missing(httpx_mock: HTTPXMock):
    base_url = "https://fw.draytek.com.tw/Vigor2926/Firmware/"

    # 1. latest.txt returns 404
    httpx_mock.add_response(
        url="https://fw.draytek.com.tw/Vigor2926/Firmware/latest.txt",
        status_code=404,
    )
    # 2. GET on base_url returns directory listing
    httpx_mock.add_response(
        url=base_url,
        method="GET",
        text=SAMPLE_ROOT_DIR_HTML,
        status_code=200,
    )
    # 3. HEAD on v3.9.9.13/
    httpx_mock.add_response(
        url="https://fw.draytek.com.tw/Vigor2926/Firmware/v3.9.9.13/",
        method="HEAD",
        status_code=200,
    )
    # 4. GET on v3.9.9.13/
    httpx_mock.add_response(
        url="https://fw.draytek.com.tw/Vigor2926/Firmware/v3.9.9.13/",
        method="GET",
        text=SAMPLE_VERSION_DIR_HTML,
        status_code=200,
    )

    with DrayTekClient() as client:
        info = client.get_latest_firmware("vigor2926", "Vigor 2926", base_url)

    assert info is not None
    assert info.version == "3.9.9.13"
    assert info.firmware_zip_name == "Vigor2926_v3.9.9.13.zip"
