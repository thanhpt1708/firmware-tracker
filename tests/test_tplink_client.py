"""Unit tests for TP-Link & Deco client parser."""

import httpx

from src.tplink_client import TPLinkClient, extract_tplink_version

MOCK_TPLINK_HTML = """
<!DOCTYPE html>
<html>
<head><title>Download for Deco M4 | TP-Link</title></head>
<body>
<div class="support-download">
    <table class="download-resource-table" role="presentation">
        <tbody>
            <tr class="basic-info">
                <th class="download-resource-name" colspan="2" scope="colgroup">
                    <p>Deco M4(EU)_V1_1.8.2 Build 20251027</p>
                </th>
                <th class="download-resource-btnbox" scope="row">
                    <a class="download-resource-btn" href="https://static.tp-link.com/upload/firmware/2025/202512/20251212/M4R_1.8.2_Build_20251027.zip">Download</a>
                </th>
            </tr>
            <tr class="detail-info">
                <td><span>Published Date: </span><span>2025-12-12</span></td>
                <td><span>Language: </span><span>Multi-language</span></td>
                <td><span>File Size: </span><span>13.68 MB</span></td>
            </tr>
            <tr class="more-info">
                <td class="more" colspan="3">
                    <p>New Features/Enhancements:<br/>1. Improved system stability.<br/>2. Added VPN support.</p>
                </td>
            </tr>
        </tbody>
    </table>
    <table class="download-resource-table" role="presentation">
        <tbody>
            <tr class="basic-info">
                <th class="download-resource-name"><p>Deco M4(EU)_V1_1.7.0</p></th>
            </tr>
        </tbody>
    </table>
</div>
</body>
</html>
"""


def test_extract_tplink_version():
    cases = [
        ("Deco M4(EU)_V1_1.8.2 Build 20251027", "1.8.2 Build 20251027"),
        ("Archer AX55(EU)_V4_251030", "251030"),
        ("Archer C6(US)_V3.20_210716", "210716"),
        ("Deco X20(US)_V1_1.5.1 Build 20210204 Rel. 50164", "1.5.1 Build 20210204"),
        ("TL-WR841N(EU)_V14_180319", "180319"),
        ("SimpleModel_1.0.0", "1.0.0"),
    ]
    for raw, expected in cases:
        assert extract_tplink_version(raw) == expected


def test_build_target_url():
    client = TPLinkClient()
    assert client.build_target_url("https://www.tp-link.com/en/support/download/deco-m4") == (
        "https://www.tp-link.com/en/support/download/deco-m4/"
    )
    assert client.build_target_url("https://www.tp-link.com/en/support/download/deco-m4/", "v1") == (
        "https://www.tp-link.com/en/support/download/deco-m4/v1/"
    )
    assert client.build_target_url("https://www.tp-link.com/en/support/download/deco-m4/", "1") == (
        "https://www.tp-link.com/en/support/download/deco-m4/v1/"
    )
    # Avoid duplicate hw_version if already in URL
    assert client.build_target_url("https://www.tp-link.com/en/support/download/deco-m4/v1/", "v1") == (
        "https://www.tp-link.com/en/support/download/deco-m4/v1/"
    )


def test_parse_download_page_success():
    client = TPLinkClient()
    info = client.parse_download_page(
        html_text=MOCK_TPLINK_HTML,
        page_url="https://www.tp-link.com/en/support/download/deco-m4/v1/",
        model_id="deco-m4-v1",
        model_name="Deco M4 (V1)",
    )

    assert info is not None
    assert info.model_id == "deco-m4-v1"
    assert info.model_name == "Deco M4 (V1)"
    assert info.version == "1.8.2 Build 20251027"
    assert info.release_date == "2025-12-12"
    assert info.firmware_size == "13.68 MB"
    assert info.firmware_zip_url == "https://static.tp-link.com/upload/firmware/2025/202512/20251212/M4R_1.8.2_Build_20251027.zip"
    assert info.firmware_zip_name == "M4R_1.8.2_Build_20251027.zip"
    assert info.brand == "tplink"
    assert "Improved system stability" in info.changelog


def test_parse_download_page_empty():
    client = TPLinkClient()
    info = client.parse_download_page(
        html_text="<html><body><p>No downloads available</p></body></html>",
        page_url="https://www.tp-link.com/empty/",
        model_id="empty-model",
        model_name="Empty Model",
    )
    assert info is None


def test_get_latest_firmware_mock_http():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        if "deco-m4" in str(request.url):
            return httpx.Response(200, text=MOCK_TPLINK_HTML)
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.Client(transport=transport)
    client = TPLinkClient(client=mock_client)

    info = client.get_latest_firmware(
        model_id="deco-m4-v1",
        model_name="Deco M4 (V1)",
        url="https://www.tp-link.com/en/support/download/deco-m4/",
        hw_version="v1",
    )
    assert info is not None
    assert info.version == "1.8.2 Build 20251027"

    notFoundInfo = client.get_latest_firmware(
        model_id="unknown",
        model_name="Unknown",
        url="https://www.tp-link.com/en/support/download/unknown/",
    )
    assert notFoundInfo is None
