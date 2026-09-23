---
name: affiliate-scout
description: "Tiêu chí và cách tìm ứng viên chương trình affiliate cho repo Affiliate-Research: scout hằng ngày theo chủ đề (AI, tài chính, chủ đề mới), lấy domain từ advertiser Google Ads Transparency, đọc ảnh chụp marketplace (PartnerStack...), loại trùng với reported_programs*.md và audited_products.md, gán status loại. Dùng khi cần tìm, lọc, chọn hay loại ứng viên affiliate, kể cả khi chỉ hỏi 'domain này đã xét chưa'."
---

# Affiliate Scout — Tìm và lọc ứng viên

## 1. Loại trùng trước tiên
Trước khi tốn công nghiên cứu, hãy chạy:

```bash
python3 .claude/skills/affiliate-scout/scripts/known_domains.py domain1.com domain2.com
python3 .claude/skills/affiliate-scout/scripts/known_domains.py --file _workspace/00_input/domains.txt
```

Domain có kết quả `KNOWN` thì bỏ qua. Ở chế độ scout, nếu cần ghi lại thì dùng status `duplicate_already_reported`. Ở chế độ audit, domain đó chỉ được đếm vào dòng "đã có trong audited_products.md". Lý do: người dùng không muốn nhận lại sản phẩm đã xem.

## 2. Chế độ scout — tiêu chí theo chủ đề

Bộ tiêu chí dưới đây được **suy ra từ lịch sử loại/chọn trong repo**. Khi người dùng đổi yêu cầu, hãy cập nhật mục này.

| Chủ đề | File lịch sử / báo cáo | Giữ lại khi | Hay bị loại vì |
|---|---|---|---|
| AI (mặc định) | `reported_programs.md` / `latest_report.md` | Sản phẩm AI **ra mắt trong năm hiện tại**, đang hoạt động, có chương trình affiliate công khai cho marketer, không cấm brand bidding | ra mắt năm trước (`rejected_not_new`), không có affiliate (`rejected_no_affiliate_found`), không xác nhận được ngày ra mắt (`rejected_unconfirmed_launch_date`), mô hình reseller/white-label/rev-share cho dev (`rejected_not_affiliate_model`) |
| tai-chinh | `reported_programs__tai-chinh.md` / `latest_report__tai-chinh.md` | Chương trình affiliate/CPA **mới công bố gần đây (vài tuần)**, cho phép marketer chạy Google Ads, sản phẩm hướng người tiêu dùng | chương trình đã có từ lâu (`rejected_not_new`), B2B hoặc API không mở cho marketer (`rejected_not_applicable`), thiếu dữ liệu (`rejected_insufficient_data`), dấu hiệu lừa đảo (WHOIS ẩn, PR trả tiền, presale token) |
| chủ đề mới | `reported_programs__{slug}.md` / `latest_report__{slug}.md` | Hỏi người dùng tiêu chí, hoặc áp dụng khung của tai-chinh | — |

Mọi chủ đề đều bị loại nếu cấm brand bidding (`rejected_brand_bidding`, do policy-checker kết luận). Danh sách status hợp lệ đầy đủ nằm ở `report-format`.

**Nguồn tìm kiếm gợi ý:** Product Hunt, Tiny Startups, Open Launch, BetaList, Hacker News "Show HN", tin gọi vốn (TechCrunch...), thư mục affiliate (PartnerStack marketplace, Impact, FlexOffers, Tolt, Rewardful, Dub partners), thông cáo báo chí về "affiliate program launch". Với tài chính, nên mở rộng theo thị trường (Trung Đông, Mỹ Latinh, Đông Nam Á, Việt Nam). Mỗi ngày nên xét **khoảng 10–20 ứng viên**, và chọn **tối đa 1–3** chương trình tốt nhất.

## 3. Chế độ audit — Google Ads Transparency
Link: `https://adstransparency.google.com/advertiser/{ID}?region={REGION}` (bỏ `region` nếu không được giao).

1. Trang được render bằng JS. Nếu WebFetch trả về trống, hãy dùng Playwright với Chromium có sẵn (`executablePath: '/opt/pw-browsers/chromium'` nếu cần), cuộn trang để tải hết creative.
2. Với mỗi creative, lấy domain đích và "Lần hiển thị gần đây nhất" (Last shown).
3. Creative được coi là **active** khi lần hiển thị gần đây nhất nằm trong 30 ngày tính từ ngày chạy.
4. Gộp theo domain, loại domain `KNOWN`, và ghi thống kê: tổng creative → số active → số domain độc nhất → số đã có trong lịch sử → **số domain mới**.

## 4. Chế độ marketplace — ảnh chụp hoặc danh sách
- Đọc ảnh bằng công cụ Read, trích tên thương hiệu, rồi tìm domain chính thức (không lấy domain của mạng affiliate).
- Bỏ qua bước lọc "Lần hiển thị gần đây nhất" và ghi rõ điều này trong đầu file audit.
- Lô lớn (hơn 20 domain) thì chia thành nhiều lô cho researcher (xem orchestrator).

## 5. Định dạng `_workspace/01_scout_candidates.md`
```markdown
# Scout {chế độ} — {chủ đề hoặc Advertiser ID} — {YYYY-MM-DD}
Thống kê: …
## Giữ lại
| Domain | Tên | Lý do giữ | Chứng cứ (URL) |
## Loại
| Domain | Tên | Status | Lý do |
```
