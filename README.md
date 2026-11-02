# 🛰️ Firmware Release Tracker & Telegram Notifier (DrayTek, Hikvision & TP-Link/Deco)

Hệ thống tự động kiểm tra và thông báo khi các hãng **DrayTek**, **Hikvision** và **TP-Link** (bao gồm cả dòng WiFi Mesh **Deco**) phát hành phiên bản firmware mới cho các dòng sản phẩm bạn quan tâm. Hệ thống chạy định kỳ từ thứ 2 đến thứ 6 hàng tuần thông qua **GitHub Actions** và gửi thông báo trực tiếp tới **Telegram**.

---

## 🌟 Tính năng nổi bật

- 🔍 **Crawl thông minh đa nền tảng**:
  - **DrayTek**: Quét kho Apache index / `latest.txt` tại `fw.draytek.com.tw`.
  - **Hikvision**: Trích xuất danh mục tài sản firmware chính hãng theo vùng (Asia/Europe).
  - **TP-Link & Deco**: Thu thập firmware mới nhất, hỗ trợ chọn Hardware Version (V1, V2...) và trích xuất điểm mới (Changelog/Release Notes) trực tiếp từ trang hỗ trợ.
- 📦 **Đầy đủ thông tin cảnh báo**: Gửi tin nhắn Telegram kèm link tải trực tiếp firmware `.zip` (kèm dung lượng), tài liệu Release Note `.pdf` hoặc trích đoạn changelog, ngày phát hành và link trang sản phẩm.
- ⚙️ **Quản lý dependencies bằng `uv`**: Tốc độ cài đặt và chạy siêu nhanh, chuẩn PEP 621 (`pyproject.toml`).
- 🔄 **Lưu trạng thái bền vững**: File `data/state.json` được tự động commit & push về Git repository sau mỗi lần phát hiện firmware mới, tránh gửi lặp thông báo.
- ⏱️ **Tự động hóa hoàn toàn với GitHub Actions**: Chạy định kỳ từ thứ 2 đến thứ 6 hàng tuần (08:00 AM UTC+7) hoặc có thể kích hoạt thủ công bất cứ lúc nào qua nút **Run workflow**.
- 🤖 **Tự động cập nhật thư viện với Dependabot**: Cấu hình tự động kiểm tra và mở Pull Request cập nhật thư viện Python và GitHub Actions vào thứ 2 hàng tuần.

---

## 📱 Mẫu thông báo Telegram

```html
🚀 CẬP NHẬT FIRMWARE DRAYTEK MỚI

📌 Thiết bị: DrayTek Vigor 2926 Series
🏷 Phiên bản: v3.9.9.13
🗓 Ngày phát hành: 2026-09-30 09:41

🔗 Tài liệu & Tải về:
• 📄 Xem Release Notes (PDF)
• 💾 Tải Vigor2926_v3.9.9.13.zip (32M)
• 📂 Mở Thư mục Firmware
```

---

## 🚀 Hướng dẫn Cài đặt & Triển khai

### 1. Chuẩn bị Telegram Bot & Chat ID

1. **Tạo Bot Telegram**:
   - Mở Telegram, tìm bot [@BotFather](https://t.me/BotFather) và gửi `/newbot`.
   - Làm theo hướng dẫn để đặt tên và username cho bot.
   - Nhận chuỗi `token` dạng: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`.
2. **Lấy Chat ID của bạn**:
   - Nhấn `/start` với bot vừa tạo.
   - Tìm bot [@userinfobot](https://t.me/userinfobot) trên Telegram và bấm `/start` để lấy `Id` của bạn (ví dụ: `123456789`).
   - *(Nếu muốn gửi vào nhóm: Thêm bot vào nhóm, gửi 1 tin nhắn bất kỳ, sau đó gọi URL `https://api.telegram.org/bot<TOKEN>/getUpdates` để tìm ID của nhóm dạng số âm `-100...`)*.

---

### 2. Cấu hình GitHub Secrets

Sau khi push repo này lên GitHub:
1. Vào repository của bạn trên GitHub -> **Settings** -> **Secrets and variables** -> **Actions**.
2. Nhấn **New repository secret** và thêm 2 secret sau:
   - `TELEGRAM_BOT_TOKEN`: Token nhận được từ `@BotFather`.
   - `TELEGRAM_CHAT_ID`: ID tài khoản hoặc nhóm Telegram của bạn.
3. Vào **Settings** -> **Actions** -> **General** -> mục **Workflow permissions**:
   - Chọn **Read and write permissions** (để GitHub Actions có quyền commit file `data/state.json` khi có bản cập nhật).
   - Nhấn **Save**.

---

### 3. Thêm / Tùy chỉnh dòng sản phẩm theo dõi

Chỉnh sửa file `config/models.yaml`. Cấu hình được phân chia rõ ràng theo từng hãng (DrayTek, Hikvision...) giúp dễ dàng quản lý và mở rộng:

```yaml
# --- DRAYTEK ROUTER & ACCESS POINT ---
draytek:
  - id: "vigor2926"
    name: "DrayTek Vigor 2926 Series"
    url: "https://fw.draytek.com.tw/Vigor2926/Firmware/"
    enabled: true

  - id: "vigor2927"
    name: "DrayTek Vigor 2927 Series"
    url: "https://fw.draytek.com.tw/Vigor2927/Firmware/"
    enabled: false

# --- HIKVISION DVR, NVR & IPC ---
# region: "Asia" (mặc định) hoặc "Europe"
hikvision:
  - id: "7208hqhi-m1-e"
    name: "Hikvision iDS-7208HQHI-M1/E"
    region: "Asia"
    enabled: true

# --- TP-LINK ROUTER & DECO MESH ---
# Hỗ trợ URL trực tiếp kèm Hardware Version (/v1/, /v2/...) hoặc URL model tổng quát
tplink:
  - id: "deco-m4-v1"
    name: "TP-Link Deco M4 (V1)"
    url: "https://www.tp-link.com/vn/support/download/deco-m4/v1/"
    enabled: true

  - id: "deco-x60-v3.2"
    name: "TP-Link Deco X60 (V3.2)"
    url: "https://www.tp-link.com/vn/support/download/deco-x60/v3.20/"
    enabled: true
```

---

## 💻 Sử dụng & Chạy thử tại máy cục bộ (Local)

Dự án sử dụng công cụ quản lý package siêu tốc [uv](https://docs.astral.sh/uv/):

### Cài đặt dependencies:
```bash
uv sync
```

### Chạy test thử quét firmware (chế độ dry-run, không gửi tin & không lưu state):
```bash
uv run python src/tracker.py check --dry-run -v
```

### Kiểm tra kết nối Telegram Bot:
Tạo file `.env` từ `.env.example`:
```bash
cp .env.example .env
# Điền TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID vào .env
```
Gửi tin nhắn test tới Telegram:
```bash
uv run python src/tracker.py test-telegram
```

### Chạy toàn bộ Unit Tests:
```bash
uv run pytest tests/ -v
```

---

## ⚙️ Các lệnh và cờ dòng lệnh hữu ích (Typer CLI)

- `check`: Lệnh quét kiểm tra các phiên bản firmware mới.
  - `--dry-run`: Quét kiểm tra thử mà không gửi tin Telegram và không lưu vào `state.json`.
  - `--force-notify`: Bắt buộc gửi thông báo ngay cả khi phiên bản đã tồn tại trong `state.json`.
  - `--model <model_id>` (hoặc `-m`): Chỉ kiểm tra 1 dòng model cụ thể (ví dụ: `-m vigor2926`).
  - `--config <path>` (hoặc `-c`): Tùy chỉnh đường dẫn file cấu hình YAML.
  - `--state <path>` (hoặc `-s`): Tùy chỉnh đường dẫn file lưu vết state JSON.
  - `-v`, `--verbose`: Bật log chi tiết debug.
- `test-telegram`: Gửi tin nhắn test xác nhận kết nối Telegram Bot.
- `--help`: Xem bảng hướng dẫn các lệnh và cờ trực tiếp trên terminal với giao diện Rich.

---

## 📂 Cấu trúc Thư mục

```
draytek-firmware-tracker/
├── .github/
│   └── workflows/
│       ├── check-firmware.yml      # Workflow định kỳ & commit state
│       └── test.yml                # Workflow chạy CI test khi push/PR
├── config/
│   └── models.yaml                 # Cấu hình danh sách thiết bị cần theo dõi
├── data/
│   └── state.json                  # File lưu trữ phiên bản đã gửi (git-tracked)
├── src/
│   ├── __init__.py
│   ├── draytek_client.py           # Crawler & Parser HTML / latest.txt của DrayTek
│   ├── notifier.py                 # Telegram Bot Notifier (định dạng HTML)
│   ├── state_manager.py            # Quản lý đọc/ghi state & so sánh phiên bản
│   └── tracker.py                  # Entrypoint điều phối luồng chạy
├── tests/
│   ├── test_draytek_client.py
│   ├── test_notifier.py
│   ├── test_state_manager.py
│   └── test_tracker.py
├── pyproject.toml                  # Khai báo cấu hình dự án & dependencies (PEP 621)
├── uv.lock                         # Lockfile xác thực dependencies
├── .env.example
├── .gitignore
└── README.md
```

---

## 📄 License
MIT License.
