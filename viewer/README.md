# Affiliate Viewer

App xem dữ liệu Google Sheet "Affiliate Research - Đối soát" (tab Trang tính1, Affiliate Research, Advertiser Audit). Chạy trên Windows và macOS (cùng một mã nguồn), chỉ ĐỌC Sheet, không sửa gì.

Có: bảng lọc và sắp xếp, lọc theo mốc thời gian, nhãn Google Ads, khung chi tiết, xuất CSV.

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

Không cần cài gì thêm: mở app, đăng nhập Google và chọn file như mục bên dưới (cần Chrome hoặc Edge trên máy).

Cấu hình và cache lưu ở: Windows `%APPDATA%\AffiliateViewer`, macOS `~/Library/Application Support/AffiliateViewer` (`config.json`, `data.json` cache Sheet). Mỗi máy một bản, bấm "Làm mới từ Google Sheet" để lấy dữ liệu mới.

## Đăng nhập Google và chọn file (không cần Google Cloud, không cần file khóa)
1. **Bước 1:** bấm **Mở Google Drive và đăng nhập**. App mở `drive.google.com/drive/home` trong một cửa sổ trình duyệt dùng hồ sơ riêng của app; anh đăng nhập tài khoản Google ở đó như bình thường (app không thấy mật khẩu).
2. **Bước 2:** trong cửa sổ Drive, bấm đúp để mở file Google Sheet muốn xem. App thấy tab đó đang mở và hiện nút **Dùng file: …**; bấm là xem được. Nút **Đổi file** ở thanh trên cùng để chọn file khác.
Cách hoạt động: app điều khiển cửa sổ trình duyệt của chính nó qua cổng gỡ lỗi chỉ mở ở `127.0.0.1` (để đọc danh sách tab và cookie phiên Google), rồi tải bản xuất "Trang web (.zip)" của Sheet bằng quyền của tài khoản đã đăng nhập. Chỉ ĐỌC. Tài khoản phải có quyền xem file, và chủ file không được tắt quyền tải xuống. Phiên đăng nhập nằm trong hồ sơ `profile/` của app; xóa thư mục này là đăng xuất.

## Đánh giá bằng Gemini (skill "global-affiliate-product-evaluator" v2)
**Từng sản phẩm:** mở chi tiết, khung **Đánh giá Gemini**, bấm **Đánh giá bằng Gemini**. Lần đầu dán khóa Gemini API của riêng mình (aistudio.google.com/apikey); khóa lưu ở `gemini_key.txt` trong thư mục dữ liệu của app (quyền 600), không nằm trong mã nguồn hay DMG.
**Hàng loạt:** nút vàng **🤖 Đánh giá Gemini** trên thanh trên cùng. Chọn số sản phẩm (tối đa 100, lấy theo thứ tự đang hiện trong bảng, đã áp bộ lọc), có thể bỏ qua sản phẩm đã có điểm và bật tra cứu web. Việc chạy nền, có thanh tiến độ và nút Dừng; chạm giới hạn lượt/phút thì tự chờ 60 giây thử lại, lỗi liên tiếp 3 lần thì tự dừng, sai khóa thì dừng ngay. Kết quả hiện ở cột **Gemini** (điểm và T1/T2/T3), có ô lọc "Gemini", thẻ "🏆 Tier 1", và sắp xếp theo điểm.
**Skill chấm 6 trụ cột (tổng 100):** Unit Economics 25 (payout, CPC hòa vốn = payout x CR, Recurring, hoàn tiền, thanh toán), Chính sách Google Ads 20, Nhu cầu và cạnh tranh Search 15 (Trends, từ khóa mua hàng), Khả năng chuyển đổi 15, Uy tín và độ bền của hãng 15 (Trustpilot, năm ra đời, cookie), Khả năng mở rộng 10. **Tier tính bằng code từ điểm các trụ cột** (không tin phép cộng của mô hình): Tier 1 khi tổng từ 75 và trụ cột Unit Economics, Chính sách Ads, Nhu cầu, Uy tín đều đạt ít nhất một nửa điểm tối đa; Tier 2 khi tổng từ 50; Tier 3 khi dưới 50 hoặc chính sách Ads gần như cấm. Kết quả có thêm CPC hòa vốn và danh sách "Cần kiểm tra thủ công" cho những gì chưa có dữ liệu.
**Sửa tiêu chí:** nội dung skill nằm ở `SKILL` trong `gemini.py`. Muốn thay mà không cần build lại, tạo file `skill.md` trong thư mục dữ liệu của app (nội dung thay hoàn toàn skill có sẵn; giữ nguyên tên 6 trụ cột để app tính điểm).
- **Google Trends** (90 ngày, toàn cầu) do app tự đọc rồi đưa vào đánh giá (`market.py`); Google đôi khi giới hạn truy vấn, khi đó ghi rõ là không đo được.
- **Trustpilot** chặn truy cập tự động nên app **không tự đọc điểm** và không cố vượt cơ chế chống bot; đánh giá chỉ kèm link và ghi "chưa đo được" (coi là thiếu dữ liệu, không phải điểm thấp). Bật **Tra cứu web** thì Gemini thử tìm điểm Trustpilot qua Google Search.
- App tự kiểm tra song song các model Flash, chỉ dùng model đang phản hồi, và nhớ model chạy tốt 24 giờ. Muốn cố định model thì đặt `gemini_model` trong `config.json`.
Kết quả lưu ở `evals.json` để không gọi lại; "Đánh giá lại" để làm mới. Toàn bộ cột của dòng sản phẩm được gửi tới Google để Gemini xử lý.

## Phát triển
- Chạy thử không mở cửa sổ: `AV_NOBROWSER=1 AV_PORT=8765 python3 app.py`, mở http://127.0.0.1:8765/
- Biến môi trường tùy chọn: `AV_SHEET_ID` (ghi đè link Sheet trong cấu hình).
- Phần khác nhau giữa hệ điều hành nằm ở `platform_util.py`.
- Tab nhận diện theo tên cột: có `Advertiser Name` là tab audit, còn lại là tab affiliate (12 cột).
