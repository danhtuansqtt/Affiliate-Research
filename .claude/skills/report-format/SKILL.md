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
- Nội dung khi **có** chương trình được chọn: mở đầu nêu số ứng viên đã rà. Với **mỗi** chương trình được chọn, BẮT BUỘC có khối 6 dòng cố định dưới đây, đúng thứ tự, đúng nhãn, mỗi dòng một giá trị đã chốt (quy tắc chốt giá trị ở mục 2b). Người dùng đọc khối này để quyết định chạy ads, nên không được gộp các dòng vào đoạn văn, không bỏ dòng nào kể cả khi thiếu dữ liệu:
  ```
  <b>Tên sản phẩm (domain)</b>
  • Tính năng: …
  • Giá bán: …
  • Hoa hồng affiliate: …
  • Google Ads: …
  • Năm ra đời: …
  • Cookie: … ngày
  • Độ đầy đủ: X/6
  ```
  Sau khối 6 dòng mới đến 1-3 câu văn xuôi: vì sao chọn, có cần duyệt không, ngưỡng rút/lịch trả, traffic, rủi ro (nguồn mâu thuẫn, mạng bị chặn…). Kết thúc báo cáo bằng câu cho biết đã lưu lịch sử. Phần liệt kê ứng viên bị loại viết ngắn, chỉ tên + lý do, để dành ký tự cho khối 6 dòng (giới hạn 4000 ký tự).
- Nội dung khi **không có** chương trình nào đạt: vẫn gửi. Kể các hướng đã tìm, các ứng viên đào sâu (`<b>Tên (domain)</b>`) và lý do loại từng cái.

## 2. `reported_programs.md` / `reported_programs__{chủ-đề}.md` — lịch sử scout
- Chỉ **nối thêm** vào cuối file, không sửa dòng cũ. Mỗi ứng viên đã xét trong lần chạy là một dòng, dù được chọn hay bị loại.
- Định dạng (từ 2026-10-01, 12 cột): `| Date | Product | Domain | Status | Note | Tính Năng | Giá Bán | Hoa Hồng Affiliate | Google Ads | Năm Ra Đời | Cookie (ngày) | Link Đăng Ký Affiliate |`. Cột cuối là URL trang/cổng đăng ký chương trình (lấy từ dòng `Link Đăng Ký Affiliate` của researcher, vd `https://partners.dub.co/{slug}/apply`; không tìm thấy thì `-`). **Google Sheet không có cột Status: cột E của Sheet là Link Đăng Ký Affiliate** (sync_sheet.py lấy cột 12 của file repo); Status vẫn bắt buộc trong file repo để chống trùng. Không để ký tự `|` trong nội dung ô. Các dòng cũ trước 2026-09-26 chỉ có 5 cột (`Date | Product | Domain | Status | Note`) — **không sửa lại dòng cũ**, `check_outputs.py` chỉ so cột với dòng MỚI.
- 6 cột thêm lấy nguyên dữ liệu từ `_workspace/02_researcher_*.md` (Tính Năng, Giá Bán, Hoa Hồng Affiliate, Năm Ra Đời, Thời Gian Cookie → ghi số ngày, vd `30`, `60`, hoặc 1 trong 4 giá trị lý do ở mục 2b) và `_workspace/02_policy_*.md` (giá trị chuẩn của cột Google Ads theo skill `brand-bidding-check`: `Bị Cấm (...)`, `Không Cấm (...)`, hoặc `Chưa xác minh — ... ({lý do theo mục 2b})`).
- **Ứng viên bị loại cũng phải điền tối đa có thể, không ghi `-` cả 6 ô** (người dùng xem Google Sheet và thấy hàng loạt dòng trống là sai). Mọi thứ scout/researcher/policy-checker đã đọc được trong lúc xét đều phải vào cột tương ứng: Tính Năng (sản phẩm làm gì, cho ai — luôn có vì scout đã đọc mô tả), Năm Ra Đời (chính là căn cứ loại `rejected_not_new`/`rejected_unconfirmed_launch_date` nên bắt buộc điền năm đã tìm thấy), Hoa Hồng Affiliate (nếu đã thấy % hoặc "không có chương trình"/"chương trình đã đóng"), Google Ads (bắt buộc `Bị Cấm (…)` cho `rejected_brand_bidding`, kèm trích ý chính), Giá Bán và Cookie nếu đã đọc. Chỉ ô thật sự chưa từng tra mới ghi `-`. Dòng `duplicate_already_reported` thì chép lại 6 ô từ dòng gốc của cùng domain.
- Chủ đề AI viết Note bằng tiếng Anh, tai-chinh viết bằng tiếng Việt (theo lịch sử hiện có). 6 cột mới luôn viết tiếng Việt cho mọi chủ đề, để khớp tiêu đề cột trên Google Sheet.
- **Status hợp lệ:** `reported`, `duplicate_already_reported`, `rejected_not_new`, `rejected_no_affiliate_found`, `rejected_not_affiliate_model`, `rejected_not_applicable`, `rejected_brand_bidding`, `rejected_insufficient_data`, `rejected_insufficient_evidence`, `rejected_unconfirmed_launch_date`, `rejected_not_ai_tool`, `rejected_not_launched_yet`, `rejected_discontinued`, `rejected_duplicate_niche`. Nếu cần thêm status mới, cập nhật đồng thời danh sách này và `STATUSES` trong `scripts/check_outputs.py`.

## 2b. Chốt giá trị cụ thể cho 6 cột (dùng chung cho khối Telegram và bảng lịch sử)
Mỗi ô chỉ chứa **một giá trị đã chốt**, theo đúng định dạng dưới đây. Không ghi khoảng giá mơ hồ ("$95-$99"), không ghi "chưa rõ thời hạn", không nhét đoạn giải thích nguồn mâu thuẫn vào ô: phần giải thích đó đưa vào cột Note (bảng lịch sử) hoặc câu văn sau khối 6 dòng (Telegram). Khi nguồn mâu thuẫn, chốt theo thứ tự ưu tiên: trang chính chủ > trang chương trình trên mạng affiliate (Dub, Tolt, Rewardful, PartnerStack, Impact…) > nguồn tổng hợp; ghi thêm nhãn tin cậy ngắn `(chính chủ)`, `(mạng affiliate)` hoặc `(nguồn phụ)` ở cuối ô.

| Cột | Định dạng bắt buộc | Ví dụ đúng | Ví dụ sai |
|---|---|---|---|
| Tính Năng | 1 câu ≤ 25 từ: làm gì, cho ai | `AI dựng website/app/game từ mô tả, cho SMB và creator` | đoạn 3-4 câu |
| Giá Bán | Từng gói `Tên gói $X/tháng` (hoặc `/năm`, `/lần`), cách nhau bằng `; `, có gói free/trial nếu có | `Free 70 credits; Premium $39.99/tháng; Platinum $79.99/tháng (chính chủ)` | `$95-$99/tháng (nguồn mâu thuẫn)` |
| Hoa Hồng Affiliate | `X% recurring N tháng` / `X% recurring trọn đời` / `X% một lần` / `$X/khách` | `15% recurring 6 tháng (chính chủ)` | `25% recurring (thời hạn chưa rõ)` |
| Google Ads | Đúng 1 trong 3 giá trị chuẩn của skill `brand-bidding-check`, trích ý chính trong ngoặc | `Không Cấm (terms chỉ cấm spam email)` · `Bị Cấm (cấm bid từ khóa "X" trên PPC)` · `Chưa xác minh — mặc định Không Cấm` | `CHƯA XÁC MINH được. Em không đọc được…` |
| Năm Ra Đời | `YYYY` hoặc `MM/YYYY` của sản phẩm (không phải ngày ra chương trình affiliate) | `01/2025` | `ra mắt khoảng đầu năm` |
| Cookie (ngày) | Chỉ số nguyên, có thể kèm nhãn nguồn; mặc định của mạng affiliate thì ghi rõ | `30` · `90 (mặc định Dub)` | `không rõ` khi chưa tra đủ |

**Ô thiếu dữ liệu phải ghi LÝ DO cụ thể, không ghi chung chung.** Người dùng cần biết thiếu vì đâu để tự đi lấy. Chỉ dùng 1 trong 4 giá trị sau (sau khi đã tra đủ số truy vấn tối thiểu ở skill `product-research`):

| Giá trị | Khi nào | Người dùng làm gì |
|---|---|---|
| `chỉ xem sau khi đăng ký ({mạng}: {link})` | Trang affiliate có nhưng số liệu/điều khoản nằm sau form đăng ký (Tolt, CellXpert, PartnerStack…) | Đăng ký rồi đọc |
| `site chặn truy cập ({mã lỗi, vd 403 từ VN})` | Chính site sản phẩm chặn, kể cả khi mở từ máy thật | Dùng VPN hoặc hỏi affiliate manager |
| `mạng cloud bị chặn — cần đọc lại {link}` | Chỉ vì sandbox bị proxy chặn, trang vẫn công khai | Đợi lượt chạy trên máy/local-runner hoặc tự mở link |
| `không công bố` | Đã tra đủ mà chủ chương trình không công khai ở đâu | Hỏi affiliate manager |

Không dùng câu `không tìm thấy dữ liệu công khai` cho dòng mới nữa (dòng cũ giữ nguyên). Ứng viên bị loại: điền những gì đã đọc được theo mục 2 (không ghi `-` hàng loạt).

**Dòng độ đầy đủ.** Trong khối 6 dòng Telegram, thêm dòng thứ 7 `• Độ đầy đủ: X/6` (X = số ô có giá trị thật, không tính 4 giá trị lý do ở trên; Google Ads "Chưa xác minh" tính là thiếu). Nếu X < 6, câu văn ngay sau khối phải liệt kê từng ô thiếu kèm việc anh cần làm (theo cột "Người dùng làm gì").

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
