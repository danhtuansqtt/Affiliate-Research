---
name: report-format
description: "Định dạng chuẩn các file đầu ra của repo Affiliate-Research: latest_report*.md (tin nhắn Telegram HTML), reported_programs*.md, advertiser-audits/*.md (bảng 10 cột), audited_products.md; bảng status hợp lệ; quy ước commit; script check_outputs.py kiểm tra trước khi commit. Dùng khi viết, sửa hay kiểm tra bất kỳ báo cáo, bảng audit hay file lịch sử nào trong repo này."
---

# Report Format — Định dạng file đầu ra

Hai workflow GitHub Actions đọc trực tiếp các file này, nên sai định dạng sẽ làm hỏng tin nhắn Telegram hoặc làm dữ liệu trên Google Sheets bị lệch:
- `telegram-notify.yml`: chạy khi `latest_report*.md` thay đổi. Nó gửi nội dung file qua Telegram với `parse_mode: HTML` và cắt ở khoảng 4000 ký tự.
- `sheets-sync.yml`: chạy khi `reported_programs__*.md` thay đổi. Nó chỉ đọc các dòng **mới thêm** trong commit cuối cùng (`HEAD~1..HEAD`). `reported_programs.md` của chủ đề AI không có `__` nên không được đồng bộ.
- Dòng của chủ đề có hậu tố `-doi` (ví dụ `reported_programs__ai-doi.md`, do routine đội agent ghi) được đồng bộ vào tab **"Affiliate Research"**. Tab này tự được tạo nếu chưa có. Các chủ đề khác ghi vào tab đầu tiên như cũ.
- Cả hai workflow **chỉ chạy khi push lên `master`**. Trước đây workflow chạy trên mọi nhánh, nên khi merge `master` vào một nhánh feature, commit merge chứa báo cáo cũ và báo cáo bị gửi Telegram/Sheets lần nữa (đã xảy ra ngày 2026-09-23). Không được bỏ bộ lọc `branches`.

## 1. `latest_report.md` / `latest_report__{chủ-đề}.md` — tin nhắn Telegram
- Viết lại toàn bộ file mỗi lần chạy. Viết văn xuôi tiếng Việt, người viết xưng "em" và gọi người đọc là "anh", giọng thân mật và báo cáo thẳng.
- Chỉ dùng các thẻ HTML Telegram hỗ trợ, chủ yếu là `<b>tên sản phẩm</b>`. Ký tự `&`, `<`, `>` trong nội dung phải viết thành `&amp;`, `&lt;`, `&gt;`. Không dùng Markdown (`**`, `#`, bảng) vì Telegram hiển thị nguyên dạng.
- Tối đa **4000 ký tự**.
- Nội dung khi **có** chương trình được chọn: mở đầu nêu số ứng viên đã rà. Với mỗi chương trình: sản phẩm là gì và vì sao là hàng mới; tình trạng brand bidding (nói rõ nếu chưa xác minh chắc chắn); giá; hoa hồng; cookie; có cần duyệt không; ngưỡng rút và lịch trả; traffic. Kết thúc bằng câu cho biết đã lưu lịch sử.
- Nội dung khi **không có** chương trình nào đạt: vẫn gửi. Kể các hướng đã tìm, các ứng viên đào sâu (`<b>Tên (domain)</b>`) và lý do loại từng cái.

## 2. `reported_programs.md` / `reported_programs__{chủ-đề}.md` — lịch sử scout
- Chỉ **nối thêm** vào cuối file, không sửa dòng cũ. Mỗi ứng viên đã xét trong lần chạy là một dòng, dù được chọn hay bị loại.
- Định dạng (từ 2026-09-26, 11 cột): `| Date | Product | Domain | Status | Note | Tính Năng | Giá Bán | Hoa Hồng Affiliate | Google Ads | Năm Ra Đời | Cookie (ngày) |`. Không để ký tự `|` trong nội dung ô. Các dòng cũ trước 2026-09-26 chỉ có 5 cột (`Date | Product | Domain | Status | Note`) — **không sửa lại dòng cũ**, `check_outputs.py` chỉ so cột với dòng MỚI.
- 6 cột thêm lấy nguyên dữ liệu từ `_workspace/02_researcher_*.md` (Tính Năng, Giá Bán, Hoa Hồng Affiliate, Năm Ra Đời, Thời Gian Cookie → ghi số ngày, vd `30`, `60`, `không tìm thấy dữ liệu công khai`) và `_workspace/02_policy_*.md` (giá trị chuẩn của cột Google Ads theo skill `brand-bidding-check`: `Bị Cấm (...)`, `Không Cấm (...)`, hoặc `không tìm thấy dữ liệu công khai — mặc định Không Cấm`).
- Ứng viên bị loại **trước khi researcher/policy-checker từng xét** (ví dụ scout tự loại vì trùng lịch sử hoặc rõ ràng không phải sản phẩm mới) thì 6 cột này ghi `-` (không phải "không tìm thấy dữ liệu công khai", để phân biệt "chưa từng tra" với "đã tra nhưng không thấy").
- Chủ đề AI viết Note bằng tiếng Anh, tai-chinh viết bằng tiếng Việt (theo lịch sử hiện có). 6 cột mới luôn viết tiếng Việt cho mọi chủ đề, để khớp tiêu đề cột trên Google Sheet.
- **Status hợp lệ:** `reported`, `duplicate_already_reported`, `rejected_not_new`, `rejected_no_affiliate_found`, `rejected_not_affiliate_model`, `rejected_not_applicable`, `rejected_brand_bidding`, `rejected_insufficient_data`, `rejected_insufficient_evidence`, `rejected_unconfirmed_launch_date`, `rejected_not_ai_tool`, `rejected_not_launched_yet`, `rejected_discontinued`, `rejected_duplicate_niche`. Nếu cần thêm status mới, cập nhật đồng thời danh sách này và `STATUSES` trong `scripts/check_outputs.py`.

## 3. `advertiser-audits/*.md` — bảng audit
Tên file:
- `{AdvertiserID}__{YYYY-MM-DD}.md` khi không có region
- `{AdvertiserID}_{REGION}__{YYYY-MM-DD}.md` khi có region
- `MARKETPLACE-BATCH__{YYYY-MM-DD}.md` cho ảnh chụp marketplace

Cấu trúc:
```markdown
# Advertiser Audit: {Tên advertiser}          ← hoặc "# Marketplace Affiliate Batch: {nguồn}"

- Advertiser ID: …
- Region: …                                   ← bỏ dòng này nếu không có
- Ngày tóm tắt: YYYY-MM-DD
- Link: https://adstransparency.google.com/advertiser/…

Tổng số creative: N. Còn active (Lần hiển thị gần đây nhất ≤30 ngày tính từ
{ngày}, tức từ {ngày-30} trở lại): M. Sau khi gộp theo domain … còn K domain độc nhất,
trong đó J domain đã có trong audited_products.md (…). Còn lại **X domain mới, độc nhất**.

⚠️ **Domain cấm bid từ khóa thương hiệu trên PPC/Google Ads**: `a.com`, `b.com` …

| STT | Tên Sản Phẩm (Domain) | Tính Năng | Điểm Nổi Bật | Giá Bán | Hoa Hồng Affiliate | Link Đăng Ký Affiliate | Thời Gian Cookie | Năm Ra Đời | Google Ads |
|---|---|---|---|---|---|---|---|---|---|
```
Mỗi dòng phải có đúng 10 cột. Nếu không có domain nào bị cấm thì bỏ khối ⚠️.

## 4. `audited_products.md` — lịch sử audit
Chỉ nối thêm, định dạng `| domain | Tên Sản Phẩm | YYYY-MM-DD | AdvertiserID hoặc MARKETPLACE-BATCH |`.

## 5. Kiểm tra trước khi commit
```bash
python3 .claude/skills/report-format/scripts/check_outputs.py <các file đã sửa>
```
Mặc định script chỉ xét các dòng mới so với `HEAD`. Thêm `--all` để soát toàn bộ file. Mọi ERROR phải sửa hết. WARN (nghi mất `$`, domain trùng) thì xem lại bằng mắt.

## 6. Commit
- **Mỗi lần chạy tạo đúng 1 commit và push ngay.** Lý do: hai workflow chỉ đọc `HEAD~1..HEAD`. Nếu gộp 2 commit rồi mới push, dữ liệu của commit đầu sẽ không được gửi Telegram hay đồng bộ Sheets.
- Message theo quy ước hiện có:
  - `daily scout YYYY-MM-DD` (AI)
  - `scout {chủ-đề} YYYY-MM-DD`
  - `Thêm audit {Tên} region={R} ({ID}) — N sản phẩm mới`
  - `Thêm audit marketplace affiliate {nguồn} — N sản phẩm mới`
- Không commit `_workspace/` (đã có trong `.gitignore`).
