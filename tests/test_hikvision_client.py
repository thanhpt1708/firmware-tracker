"""Unit tests for Hikvision client and scraper using pytest-httpx."""

from pytest_httpx import HTTPXMock

from src.hikvision_client import HikvisionClient, format_file_size

SAMPLE_HIKVISION_CATALOG_HTML = """
<!DOCTYPE HTML>
<html>
<head><title>Firmware Download</title></head>
<body>
<div class="nav-item isShowMain" data-main-tag="Turbo-HD-Products" data-sub-tag="DVR">
    <div class="main-title">
        <a class="link" href="/en/products/Turbo-HD-Products/DVR/Value-Series/ids-7208hqhi-m1-e/">IDS-7208HQHI-M1/E</a>
    </div>
    <div class="child-content">
        <div class="main-item">
            <div class="firmware-section">
                <div class="firmware-title topic">Firmware</div>
                <ul class="firmware-asstes">
                    <li class="assets-box">
                        <a class="assets" data-title="Firmware_Asia_V4.84.011_251217" data-href="https://assets.hikvision.com/prd/normal/all/files/202603/Firmware_Asia_V4.84.011_251217_S3000693361.zip">Firmware_Asia_V4.84.011_251217</a>
                    </li>
                    <li class="assets-box">
                        <a class="assets" data-title="Firmware_Europe_V4.84.011_251217" data-href="https://assets.hikvision.com/prd/normal/all/files/202603/Firmware_Europe_V4.84.011_251217_S3000693333.zip">Firmware_Europe_V4.84.011_251217</a>
                    </li>
                </ul>
            </div>
            <div class="release-section">
                <div class="release-title topic">Release notes:</div>
                <ul class="release-asstes">
                    <li class="assets-box">
                        <a class="assets" data-href="https://assets.hikvision.com/prd/normal/all/files/202603/releasenote%5CTurbo_HD_DVR_V4.84.011build251217_Release_Notes.pdf">Turbo HD DVR V4.84.011build251217 Release Notes</a>
                    </li>
                </ul>
            </div>
            <div class="sub-section">
                <div class="applied-title">Applied to:</div>
                <ul class="sub-list">
                    <li class="sub-item">iDS-7208HQHI-M1/E(E)</li>
                </ul>
            </div>
        </div>
    </div>
</div>
<div class="nav-item isShowMain" data-main-tag="Network-Camera" data-sub-tag="IPC">
    <div class="main-title">
        <a class="link" href="/en/products/Network-Camera/IPC/ds-2cd2043g2-i/">DS-2CD2043G2-I</a>
    </div>
    <div class="child-content">
        <div class="firmware-section">
            <ul class="firmware-asstes">
                <li class="assets-box">
                    <a class="assets" data-title="Firmware_V5.7.13_230712" data-href="https://assets.hikvision.com/files/IPC_G2_V5.7.13_230712.zip">Firmware</a>
                </li>
            </ul>
        </div>
    </div>
</div>
</body>
</html>
"""


def test_format_file_size():
    assert format_file_size(500) == "500B"
    assert format_file_size(2048) == "2K"
    assert format_file_size(33392366) == "31.8M"
    assert format_file_size(1073741824) == "1.0G"


def test_find_model_block():
    client = HikvisionClient()
    # Test match with slash
    block1 = client.find_model_block(SAMPLE_HIKVISION_CATALOG_HTML, "7208hqhi-m1/e")
    assert block1 is not None
    assert "IDS-7208HQHI-M1/E" in block1

    # Test match with prefix
    block2 = client.find_model_block(SAMPLE_HIKVISION_CATALOG_HTML, "ids-7208hqhi-m1-e")
    assert block2 is not None
    assert "IDS-7208HQHI-M1/E" in block2

    # Test match IPC
    block3 = client.find_model_block(SAMPLE_HIKVISION_CATALOG_HTML, "ds-2cd2043g2-i")
    assert block3 is not None
    assert "DS-2CD2043G2-I" in block3

    # Test not found
    block4 = client.find_model_block(SAMPLE_HIKVISION_CATALOG_HTML, "non-existent-model")
    assert block4 is None


def test_parse_model_block_asia_region(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://assets.hikvision.com/prd/normal/all/files/202603/Firmware_Asia_V4.84.011_251217_S3000693361.zip",
        method="HEAD",
        headers={"content-length": "33392366"},
        status_code=200,
    )

    client = HikvisionClient()
    block = client.find_model_block(SAMPLE_HIKVISION_CATALOG_HTML, "7208hqhi-m1/e")
    assert block is not None

    info = client.parse_model_block(block, "7208hqhi-m1-e", "Hikvision 7208", region="Asia")
    assert info is not None
    assert info.brand == "hikvision"
    assert info.model_id == "7208hqhi-m1-e"
    assert info.model_name == "IDS-7208HQHI-M1/E"
    assert info.version == "4.84.011"
    assert info.release_date == "2025-12-17"
    assert "Firmware_Asia" in (info.firmware_zip_url or "")
    assert info.firmware_size == "31.8M"
    assert info.release_note_url is not None


def test_parse_model_block_europe_region(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://assets.hikvision.com/prd/normal/all/files/202603/Firmware_Europe_V4.84.011_251217_S3000693333.zip",
        method="HEAD",
        headers={"content-length": "33392366"},
        status_code=200,
    )

    client = HikvisionClient()
    block = client.find_model_block(SAMPLE_HIKVISION_CATALOG_HTML, "7208hqhi-m1/e")
    assert block is not None

    info = client.parse_model_block(block, "7208hqhi-m1-e", "Hikvision 7208", region="Europe")
    assert info is not None
    assert "Firmware_Europe" in (info.firmware_zip_url or "")


def test_get_latest_firmware_end_to_end(httpx_mock: HTTPXMock):
    catalog_url = "https://www.hikvision.com/en/support/download/firmware/"

    httpx_mock.add_response(
        url=catalog_url,
        method="GET",
        text=SAMPLE_HIKVISION_CATALOG_HTML,
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://assets.hikvision.com/prd/normal/all/files/202603/Firmware_Asia_V4.84.011_251217_S3000693361.zip",
        method="HEAD",
        headers={"content-length": "33392366"},
        status_code=200,
    )

    with HikvisionClient() as client:
        info = client.get_latest_firmware(
            model_id="7208hqhi-m1-e",
            model_name="Hikvision iDS-7208HQHI-M1/E",
            catalog_url=catalog_url,
            region="Asia",
        )

    assert info is not None
    assert info.version == "4.84.011"
    assert info.model_id == "7208hqhi-m1-e"


def test_fetch_catalog_solves_edgeone_challenge(httpx_mock: HTTPXMock):
    catalog_url = "https://www.hikvision.com/en/support/download/firmware/"
    challenge_html = (
        '<script>function a(a){function n(){for(var a={wQzOV:_0x649a("0x4"),'
        'iTyzs:function(a,n){return a+n}},n=a[_0x649a("0x5")][_0x649a("0x6")]("|"),e=0;;)'
        '{switch(n[e++]){case"0":t+="EO_Bot_Ssid=";continue;case"1":return t;'
        'case"2":t+="";continue;case"3":t=a[_0x649a("0x7")](t,601620480);continue;'
        'case"4":var t="";continue}break}}var e={WTKkN:122760035,bOYDu:944346978,'
        'dtzqS:function(a,n){return a+n},wyeCN:1396148637,pCQRM:function(a){return a()}},'
        't=0;return t+=e[_0x649a("0x0")],t+=e[_0x649a("0x1")],t=e[_0x649a("0x2")](t,e[_0x649a("0x3")]),'
        '[t,e[_0x649a("0x8")](n)][a]}document[_0x649a("0x9")]="__tst_status="+a(0)+"#;";</script>'
    )

    httpx_mock.add_response(
        url=catalog_url,
        method="GET",
        text=challenge_html,
        headers={"set-cookie": "path=/", "server": "TencentEdgeOne"},
        status_code=200,
    )
    httpx_mock.add_response(
        url=catalog_url,
        method="GET",
        text=SAMPLE_HIKVISION_CATALOG_HTML,
        status_code=200,
    )

    with HikvisionClient() as client:
        html = client.fetch_catalog(catalog_url)
        assert html == SAMPLE_HIKVISION_CATALOG_HTML
        assert client.client.cookies.get("__tst_status") == "2463255650#"
        assert client.client.cookies.get("EO_Bot_Ssid") == "601620480"


