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

## Chạy trên Windows

`viewer\dist\AffiliateViewer.exe` (build bằng `python -m PyInstaller --noconfirm --onefile --windowed --name AffiliateViewer --add-data "index.html;." app.py`). Hoặc chạy thẳng `python app.py`.

## Cài đặt lần đầu (cả hai hệ điều hành)

App hỏi 2 thứ, chỉ một lần, vì chúng không nằm trong mã nguồn (repo công khai):
1. **File khóa Google service account** (`*-sa-key.json`). App tự tìm trong `~/Downloads`, `~/.config/affiliate-viewer/`, `~/.secrets/`; không thấy thì bấm "Chọn file khóa…". Chuyển file sang Mac bằng AirDrop hoặc trình quản lý mật khẩu; không commit vào repo.
2. **Link Google Sheet**: dán link `https://docs.google.com/spreadsheets/d/…` vào ô trên màn hình đầu.

Cấu hình và cache lưu ở: Windows `%APPDATA%\AffiliateViewer`, macOS `~/Library/Application Support/AffiliateViewer` (`config.json`, `data.json` cache Sheet, `vip.json` kết quả Check VIP). Mỗi máy một bản, bấm "Làm mới từ Google Sheet" để lấy dữ liệu mới.

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
