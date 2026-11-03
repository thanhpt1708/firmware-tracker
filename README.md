# 🛰️ Firmware Release Tracker & Telegram Notifier (DrayTek, Hikvision & TP-Link/Deco)

Hệ thống tự động kiểm tra và thông báo khi các hãng **DrayTek**, **Hikvision** và **TP-Link** (bao gồm cả dòng WiFi Mesh **Deco**) phát hành phiên bản firmware mới cho các dòng sản phẩm bạn theo dõi. Hệ thống chạy định kỳ tự động thông qua **GitHub Actions** và gửi thông báo trực tiếp tới **Telegram**.

---

## 🌟 Tính năng nổi bật

- 🔍 **Crawl thông minh đa nền tảng**:
  - **DrayTek**: Quét kho Apache index / `latest.txt` tại `fw.draytek.com.tw`, bóc tách dung lượng file và tài liệu Release Notes `.pdf`.
  - **Hikvision**: Trích xuất catalog chính thức từ cổng hỗ trợ, tự động giải mã và vượt qua cơ chế bot challenge **Tencent EdgeOne** bằng sandbox **Node.js VM** (kèm cơ chế regex fallback), hỗ trợ phân vùng (Asia, Europe...).
  - **TP-Link & Deco**: Tự động bóc tách Hardware Version (V1, V2...), trích xuất điểm mới (Release Notes / Changelog) và link tải firmware trực tiếp từ trang hỗ trợ TP-Link.
- 🛡️ **Kiến trúc Crawler chuẩn hóa (`BaseCrawlerClient`)**:
  - Tích hợp `httpx` hỗ trợ HTTP/2, đồng bộ User-Agent chuẩn browser hiện đại, cấu hình timeout và quản lý kết nối an toàn.
- 📦 **Nội dung thông báo Telegram trực quan**:
  - Tin nhắn định dạng HTML sinh động kèm link tải trực tiếp firmware `.zip` (hiển thị dung lượng file), tài liệu Release Note `.pdf` hoặc changelog chi tiết, ngày phát hành và link thư mục/trang hỗ trợ.
- ⚙️ **Quản lý dự án siêu tốc với `uv` & Python 3.14**:
  - Tuân thủ chuẩn PEP 621 (`pyproject.toml`), xác thực gói qua `uv.lock`.
- 🔄 **Lưu trạng thái bền vững & chống trùng lặp**:
  - Quản lý phiên bản qua file `data/state.json`, tự động commit & push về Git repository sau mỗi lần phát hiện firmware mới.
  - Hỗ trợ cờ `--notify-on-init` (bật/tắt thông báo cho thiết bị mới thêm lần đầu) và `--force-notify`.
- ⏱️ **Tự động hóa hoàn toàn với GitHub Actions**:
  - Chạy định kỳ từ thứ 2 đến thứ 6 hàng tuần (08:00 AM UTC+7).
  - Hỗ trợ kích hoạt thủ công (**Run workflow**) với đầy đủ tùy chọn: lọc theo `brand`, `model`, chạy thử `dry_run`, ép gửi `force_notify`, kiểm soát `notify_on_init`, và bật debug log `verbose`.
- 🧪 **Kiểm thử & Chất lượng mã nguồn**:
  - Kiểm định kiểu dữ liệu với **Pydantic v2**, giao diện dòng lệnh bằng **Typer**, kiểm thử toàn diện với **pytest**, và lint/format tự động với **ruff**.

---

## 📱 Mẫu thông báo Telegram

````carousel
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
<!-- slide -->
```html
🚀 CẬP NHẬT FIRMWARE HIKVISION MỚI

📌 Thiết bị: Hikvision iDS-7208HQHI-M1/E
🏷 Phiên bản: V4.75.002_build260814
🗓 Ngày phát hành: 2026-08-14

🔗 Tài liệu & Tải về:
• 💾 Tải Firmware (ZIP) (35.2M)
• 📂 Cổng Firmware Hikvision
```
<!-- slide -->
```html
🚀 CẬP NHẬT FIRMWARE TP-LINK MỚI

📌 Thiết bị: TP-Link Deco M4 (V1)
🏷 Phiên bản: 1.5.8 Build 20260715
🗓 Ngày phát hành: 2026-07-20

📝 Điểm mới:
1. Cải thiện độ ổn định kết nối Mesh.
2. Nâng cao tính bảo mật cho giao diện Web.

🔗 Tài liệu & Tải về:
• 💾 Tải Firmware (ZIP) (14.6M)
• 📂 Trang Hỗ trợ TP-Link
```
````

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
   - *(Nếu gửi vào nhóm: Thêm bot vào nhóm, gửi 1 tin nhắn bất kỳ, sau đó gọi URL `https://api.telegram.org/bot<TOKEN>/getUpdates` để tìm ID nhóm dạng số âm `-100...`)*.

---

### 2. Cấu hình GitHub Secrets & Quyền hạn

Sau khi push repo này lên GitHub:
1. Vào repository của bạn trên GitHub -> **Settings** -> **Secrets and variables** -> **Actions**.
2. Nhấn **New repository secret** và thêm 2 secret sau:
   - `TELEGRAM_BOT_TOKEN`: Token nhận được từ `@BotFather`.
   - `TELEGRAM_CHAT_ID`: ID tài khoản hoặc nhóm Telegram của bạn.
3. Vào **Settings** -> **Actions** -> **General** -> mục **Workflow permissions**:
   - Chọn **Read and write permissions** (để GitHub Actions có quyền commit file `data/state.json` khi có bản cập nhật).
   - Nhấn **Save**.

---

### 3. Cấu hình danh sách thiết bị theo dõi (`config/models.yaml`)

Chỉnh sửa file `config/models.yaml`. Cấu hình được phân chia theo từng hãng (`draytek`, `hikvision`, `tplink`):

```yaml
# ==============================================================================
# 1. DRAYTEK ROUTER & ACCESS POINT
# ==============================================================================
draytek:
  - id: "vigor2926"
    name: "DrayTek Vigor 2926 Series"
    url: "https://fw.draytek.com.tw/Vigor2926/Firmware/"
    enabled: true

  - id: "vigor2927"
    name: "DrayTek Vigor 2927 Series"
    url: "https://fw.draytek.com.tw/Vigor2927/Firmware/"
    enabled: false

# ==============================================================================
# 2. HIKVISION DVR, NVR & IPC
# ==============================================================================
hikvision:
  - id: "7208hqhi-m1-e"
    name: "Hikvision iDS-7208HQHI-M1/E"
    region: "Asia"          # "Asia" (mặc định cho VN) hoặc "Europe"
    enabled: true

  - id: "ds-2cd1043g2-liuf"
    name: "Hikvision DS-2CD1043G2-LIUF"
    region: "Asia"
    enabled: true

# ==============================================================================
# 3. TP-LINK ROUTER & DECO MESH
# ==============================================================================
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

#### Các trường cấu hình (`ModelConfig`):
- `id` *(bắt buộc)*: Định danh duy nhất của thiết bị (viết liền, không dấu).
- `name` *(bắt buộc)*: Tên hiển thị khi gửi thông báo Telegram.
- `url` *(tùy chọn)*: Link trang download/firmware. Đối với Hikvision và TP-Link, hệ thống có thể tự suy luận URL mặc định nếu để trống.
- `brand` *(tùy chọn)*: Hãng (`draytek`, `hikvision`, `tplink`). Tự động nhận diện khi đặt dưới mục tương ứng trong YAML.
- `region` *(tùy chọn, Hikvision)*: Khu vực tìm kiếm catalog (`Asia` hoặc `Europe`). Mặc định: `Asia`.
- `hw_version` *(tùy chọn, TP-Link)*: Phiên bản phần cứng (ví dụ: `v1`, `v2`, `v3.2`).
- `model_name_match` *(tùy chọn, Hikvision)*: Chuỗi tùy chỉnh khớp trong catalog nếu tên hiển thị khác tên danh mục.
- `enabled`: Bật (`true`) hoặc tắt (`false`) theo dõi model này.

---

## 💻 Sử dụng & Chạy thử tại máy cục bộ (Local)

Dự án yêu cầu **Python >= 3.14** và sử dụng trình quản lý package siêu tốc [uv](https://docs.astral.sh/uv/):

### 1. Cài đặt dependencies:
```bash
uv sync
```
*(Lưu ý: Để giải mã thử thách JS Tencent EdgeOne của Hikvision tối ưu nhất, khuyến nghị máy có sẵn Node.js 18+; nếu không có, crawler sẽ tự động dùng regex fallback).*

### 2. Thiết lập biến môi trường:
Tạo file `.env` từ file mẫu:
```bash
cp .env.example .env
# Chỉnh sửa .env và điền TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

### 3. Kiểm tra kết nối Telegram Bot:
```bash
uv run python src/tracker.py test-telegram
```

### 4. Chạy quét kiểm tra firmware:
- **Chạy thử nghiệm (dry-run)** (không gửi tin Telegram, không ghi `state.json`):
  ```bash
  uv run python src/tracker.py check --dry-run -v
  ```
- **Chỉ quét một hãng cụ thể**:
  ```bash
  uv run python src/tracker.py check --brand tplink --dry-run
  ```
- **Chỉ quét một thiết bị cụ thể**:
  ```bash
  uv run python src/tracker.py check --model deco-m4-v1 --dry-run
  ```
- **Bắt buộc gửi thông báo (bỏ qua cache trạng thái)**:
  ```bash
  uv run python src/tracker.py check --model vigor2926 --force-notify
  ```

### 5. Kiểm thử & Kiểm tra chất lượng mã nguồn:
```bash
# Chạy toàn bộ Unit Tests
uv run pytest tests/ -v

# Kiểm tra code style & linting
uv run ruff check .

# Kiểm tra định dạng code
uv run ruff format --check .
```

---

## ⚙️ Các lệnh và Cờ dòng lệnh (Typer CLI)

Entrypoint chính là `src/tracker.py`:

```bash
uv run python src/tracker.py [COMMAND] [OPTIONS]
```

### Lệnh `check` (hoặc chạy mặc định):
| Tùy chọn | Viết tắt | Mặc định | Mô tả |
| :--- | :---: | :---: | :--- |
| `--brand` | `-b` | `""` | Lọc kiểm tra theo hãng (`draytek`, `hikvision`, `tplink`). Để trống để quét tất cả. |
| `--model` | `-m` | `""` | Chỉ kiểm tra 1 dòng model cụ thể theo `id`. |
| `--dry-run` | | `False` | Quét thử nghiệm; không gửi tin nhắn Telegram và không lưu vào `state.json`. |
| `--force-notify` | | `False` | Bắt buộc gửi thông báo ngay cả khi phiên bản đã được lưu trước đó. |
| `--notify-on-init` / `--no-notify-on-init` | | `True` | Có gửi thông báo khi lần đầu tiên theo dõi một model mới hay không (hoặc qua biến môi trường `NOTIFY_ON_INIT`). |
| `--config` | `-c` | `config/models.yaml` | Đường dẫn tới file cấu hình YAML. |
| `--state` | `-s` | `data/state.json` | Đường dẫn tới file lưu trữ trạng thái JSON. |
| `--verbose` | `-v` | `False` | Bật chế độ ghi log chi tiết (bao gồm cả HTTP headers/requests). |

### Lệnh `test-telegram`:
Gửi tin nhắn mẫu kiểm tra xác thực `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID`.

---

## 🤖 GitHub Actions Workflow

Workflow được định nghĩa tại `.github/workflows/check-firmware.yml`:

- **Chạy định kỳ tự động**: Lịch cron `0 1 * * 1-5` (Thứ 2 đến Thứ 6 hàng tuần lúc 08:00 AM UTC+7).
- **Kích hoạt thủ công (`workflow_dispatch`)**: Hỗ trợ đầy đủ các input tùy biến:
  - `brand`: Lựa chọn hãng muốn quét (`all`, `draytek`, `hikvision`, `tplink`).
  - `model`: Nhập ID thiết bị cụ thể muốn quét (tùy chọn).
  - `dry_run`: Chế độ chạy thử, không gửi cảnh báo và không commit state (`true`/`false`).
  - `force_notify`: Bắt buộc gửi thông báo Telegram (`true`/`false`).
  - `notify_on_init`: Bật/tắt thông báo khi thêm model mới lần đầu (`true`/`false`).
  - `verbose`: Bật log chi tiết debug crawler trong Actions log (`true`/`false`).

Khi phát hiện có bản cập nhật mới (ở chế độ thường), workflow sẽ tự động commit và push file `data/state.json` với commit message `chore(state): update firmware tracking state [skip ci]`.

---

## 📂 Cấu trúc Thư mục

```
firmware-tracker/
├── .github/
│   └── workflows/
│       ├── check-firmware.yml      # Workflow định kỳ & kích hoạt thủ công
│       └── test.yml                # Workflow CI chạy tests khi push/PR
├── assets/
│   └── bot-avatar.jpg              # Ảnh đại diện cho Telegram Bot
├── config/
│   └── models.yaml                 # Cấu hình danh sách thiết bị cần theo dõi
├── data/
│   └── state.json                  # Lưu trữ phiên bản firmware mới nhất đã gửi
├── src/
│   ├── __init__.py
│   ├── config.py                   # Pydantic models & validation cấu hình
│   ├── draytek_client.py           # Crawler & Parser cho DrayTek
│   ├── hikvision_client.py         # Crawler & Parser cho Hikvision (vượt EdgeOne JS challenge)
│   ├── http_client.py              # Base crawler client (HTTP/2, headers, retry)
│   ├── notifier.py                 # Module gửi thông báo Telegram (HTML)
│   ├── state_manager.py            # Quản lý đọc/ghi state & so sánh phiên bản
│   ├── tplink_client.py            # Crawler & Parser cho TP-Link / Deco Mesh
│   └── tracker.py                  # Entrypoint CLI điều phối luồng chạy
├── tests/
│   ├── test_config.py              # Unit tests cấu hình Pydantic & YAML
│   ├── test_draytek_client.py      # Unit tests DrayTek client
│   ├── test_hikvision_client.py    # Unit tests Hikvision client & JS solver
│   ├── test_http_client.py         # Unit tests HTTP client & headers
│   ├── test_notifier.py            # Unit tests Telegram notifier
│   ├── test_state_manager.py       # Unit tests quản lý trạng thái
│   ├── test_tplink_client.py       # Unit tests TP-Link client & changelog
│   └── test_tracker.py             # Unit tests CLI & orchestration flow
├── pyproject.toml                  # Cấu hình dự án, dependencies & Ruff (PEP 621)
├── uv.lock                         # Lockfile xác thực toàn vẹn dependencies
├── .env.example                    # File mẫu khai báo biến môi trường
├── .gitignore
└── README.md
```

---

## 📄 License

Mã nguồn được phân phối dưới giấy phép [MIT License](LICENSE).
