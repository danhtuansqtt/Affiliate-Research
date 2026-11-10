# Affiliate Viewer

App xem dữ liệu Google Sheet "Affiliate Research - Đối soát" (tab Trang tính1, Affiliate Research, Advertiser Audit). Chạy trên Windows và macOS (cùng một mã nguồn), chỉ ĐỌC Sheet, không sửa gì.

Có: bảng lọc và sắp xếp, lọc theo mốc thời gian, nhãn Google Ads, khung chi tiết, xuất CSV, và nút vàng **Check VIP** (Google Trends 30 ngày, Trustpilot, Google News, Hacker News, tuổi domain, điểm VIP 0–100).

## Chạy trên macOS

Cần: Python 3 (`brew install python`) và Chrome hoặc Edge (có sẵn thì app mở thành cửa sổ riêng; không có thì mở bằng trình duyệt mặc định).

```bash
cd ~/Affiliate-Research
bash viewer/run-mac.command        # hoặc bấm đúp file viewer/run-mac.command trong Finder
```

Lần đầu script tự tạo môi trường Python riêng (`~/.affiliate-viewer-venv`) và cài `google-auth`, `certifi`.

Muốn có ứng dụng `.app` để kéo vào Applications (phải build TRÊN Mac):

```bash
bash viewer/build-mac.sh           # ra viewer/dist/AffiliateViewer.app
```

## Cài bằng file .dmg (MacBook chip M1/M2/M3/M4)

GitHub tự dựng file `.dmg` trên máy macOS mỗi khi thư mục `viewer/` đổi:

1. Mở https://github.com/danhtuansqtt/Affiliate-Research/actions/workflows/build-mac-dmg.yml (đăng nhập GitHub).
2. Chọn lần chạy mới nhất có dấu tích xanh, kéo xuống mục **Artifacts**, tải `AffiliateViewer-mac-arm64` (file .zip, giải nén ra `AffiliateViewer.dmg`). File được giữ 30 ngày; hết hạn thì vào tab Actions bấm **Run workflow** để dựng lại.
3. Mở `.dmg`, kéo **Affiliate Viewer** vào **Applications**.
4. Lần đầu mở: macOS báo "không xác minh được nhà phát triển" vì app chưa ký bằng tài khoản Apple Developer. Bấm chuột phải vào app > **Open** > **Open**, hoặc vào System Settings > Privacy & Security > **Open Anyway**. Chỉ cần làm một lần.

Mac đời Intel: chưa có bản `.dmg` (workflow dựng cho chip Apple). Dùng `bash viewer/run-mac.command` ở trên, hoặc tự dựng bằng `bash viewer/build-dmg.sh` trên chính máy đó.

## Chạy trên Windows

`viewer\dist\AffiliateViewer.exe` (build bằng `python -m PyInstaller --noconfirm --onefile --windowed --name AffiliateViewer --add-data "index.html;." app.py`). Hoặc chạy thẳng `python app.py`.

## Cài đặt lần đầu (cả hai hệ điều hành)

App hỏi 2 thứ, chỉ một lần, vì chúng không nằm trong mã nguồn (repo công khai):
1. **File khóa Google service account** (`*-sa-key.json`). App tự tìm trong `~/Downloads`, `~/.config/affiliate-viewer/`, `~/.secrets/`; không thấy thì bấm "Chọn file khóa…". Chuyển file sang Mac bằng AirDrop hoặc trình quản lý mật khẩu; không commit vào repo.
2. **Link Google Sheet**: dán link `https://docs.google.com/spreadsheets/d/…` vào ô trên màn hình đầu.

Cấu hình và cache lưu ở: Windows `%APPDATA%\AffiliateViewer`, macOS `~/Library/Application Support/AffiliateViewer` (`config.json`, `data.json` cache Sheet, `vip.json` kết quả Check VIP). Mỗi máy một bản, bấm "Làm mới từ Google Sheet" để lấy dữ liệu mới.

## Đăng nhập Google và chọn file từ Drive
App chỉ có hai bước: bấm **Đăng nhập Google**, rồi chọn một file Google Sheet trong danh sách Drive của anh (gồm file của mình và file được chia sẻ; có ô tìm theo tên). Nút **Đổi file** ở thanh trên cùng để chọn file khác, **Đăng xuất** để thoát tài khoản.
Một lần duy nhất, trên [Google Cloud Console](https://console.cloud.google.com/):
1. Tạo dự án, bật **Google Sheets API** và **Google Drive API**.
2. *OAuth consent screen*: loại External, thêm email của anh vào Test users.
3. *Credentials > Create credentials > OAuth client ID > Desktop app*, tải file `client_secret_….json`. Để file này trong `~/Downloads` (app tự tìm); nếu không thấy, lần đăng nhập đầu app sẽ hỏi chọn file.
App xin quyền xem Google Sheets và xem tên/danh sách file Drive (chỉ đọc, không sửa, không đọc nội dung file khác). Token lưu ở `google_token.json` trong thư mục dữ liệu của app (quyền 600). Không commit file OAuth vào repo.
(Cách file khóa service account cũ vẫn chạy ngầm nếu máy đã có file khóa, nhưng không còn hiện trên giao diện.)

## Check VIP
Nút vàng trên thanh trên cùng: chọn phạm vi (các dòng đang lọc, tối đa N) và nguồn, chạy nền.
- Nguồn (không cần khóa API): Google Trends 30 ngày, Trustpilot (qua Chrome/Edge chạy ẩn vì trang chặn đọc thông thường), Google News (30/7 ngày), Hacker News (30 ngày), tuổi domain (RDAP, dự phòng Wayback).
- Điểm VIP 0–100: quan tâm (Trends TB) 25 + đà tăng 20 + uy tín Trustpilot 20 + truyền thông 15 + phù hợp chạy ads (Google Ads, độ đầy đủ, có link đăng ký) 20. Nguồn lỗi thì bỏ phần đó, không bị trừ điểm. Công thức ở `vipScore()` trong `index.html`.
- Từ khóa = tên sản phẩm đã bỏ phần trong ngoặc; tên chung chung (vd "Incredible") cho số liệu nhiễu.

## Phát triển
- Chạy thử không mở cửa sổ: `AV_NOBROWSER=1 AV_PORT=8765 python3 app.py`, mở http://127.0.0.1:8765/
- Biến môi trường tùy chọn: `AV_SHEET_ID` (ghi đè link Sheet trong cấu hình).
- Phần khác nhau giữa hệ điều hành nằm ở `platform_util.py`.
- Tab nhận diện theo tên cột: có `Advertiser Name` là tab audit, còn lại là tab affiliate (12 cột).
