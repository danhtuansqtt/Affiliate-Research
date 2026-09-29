---
name: brand-bidding-check
description: "Soát điều khoản chương trình affiliate về quảng cáo trả phí: cấm bid từ khóa thương hiệu (brand bidding / trademark bidding / branded keywords), cấm PPC hoặc Google Ads, cấm direct linking, giới hạn quốc gia; điền cột 'Google Ads' theo giá trị chuẩn. Dùng mỗi khi cần biết một chương trình affiliate có cho chạy Google Ads hay không, hoặc khi kiểm tra lại cảnh báo ⚠️ trong file audit."
---

# Brand Bidding Check — Soát chính sách quảng cáo

Người dùng kiếm hoa hồng bằng cách chạy Google Ads trỏ về link affiliate. Vì vậy câu hỏi quan trọng nhất cho mỗi chương trình là: **có được bid tên thương hiệu và chạy Google Ads không?**

## Tìm điều khoản ở đâu
1. Trang affiliate chính chủ (`/affiliate`, `/partners`, `/affiliate-terms`, FAQ).
2. Trang chương trình trên mạng affiliate (PartnerStack, Impact, Tolt, Rewardful, FirstPromoter, Dub, FlexOffers, ShareASale).
3. Truy vấn gợi ý: `"{brand}" affiliate terms "brand" bidding`, `"{brand}" affiliate "PPC"`, `"{brand}" affiliate "trademark" keywords`, `"{brand}" affiliate "paid search"`.

Nếu WebFetch bị proxy chặn (403), dùng WebSearch với các truy vấn trên kèm `site:{domain}` hoặc `site:partnerstack.com`. Nếu vẫn không thấy câu chữ điều khoản thì dùng kết luận mặc định kèm độ tin cậy thấp, và ghi thêm "mạng bị chặn" để orchestrator báo người dùng.

Các cụm từ thường gặp trong điều khoản:
- **Cấm:** "may not bid on", "trademark/branded keywords", "brand terms", "no PPC", "paid search is prohibited", "negative keyword".
- **Cho phép:** "Paid ads (Google, Facebook…) are allowed".

## Giá trị chuẩn cho cột Google Ads
Luôn chọn **đúng một** trong các giá trị sau, rồi ghi chi tiết trong ngoặc:

| Tình huống | Giá trị |
|---|---|
| Điều khoản cấm bid brand, hoặc cấm PPC/Google Ads | `Bị Cấm ({phạm vi cấm, ví dụ: cấm bid từ khóa thương hiệu "X" trên PPC; các chiến dịch khác được phép})` |
| Điều khoản ghi rõ là được phép | `Không Cấm ({trích ý chính})` |
| Không tìm thấy điều khoản | `Chưa xác minh — mặc định Không Cấm ({lý do theo mục 2b skill report-format})`, ví dụ `Chưa xác minh — mặc định Không Cấm (chỉ xem sau khi đăng ký Tolt: voicedash.tolt.io)` hoặc `(mạng cloud bị chặn — cần đọc lại {link terms})` hoặc `(không công bố; đã tra terms site + Dub)` |

Direct linking và giới hạn quốc gia được ghi thêm trong ngoặc nếu có, vì chúng cũng ảnh hưởng tới việc chạy ads.

**Tra đủ trước khi dùng giá trị mặc định.** Chỉ được kết luận `Chưa xác minh — mặc định Không Cấm` sau khi đã chạy ít nhất 4 truy vấn khác nhau cho domain đó và liệt kê chúng ở dòng `Đã tra:`:
1. `site:{domain} affiliate terms` (hoặc `/affiliate-terms`, `/partner-terms`)
2. trang chương trình trên mạng affiliate: `site:partners.dub.co {slug}`, `site:tolt.io {brand}`, `site:getrewardful.com {brand}`, `site:partnerstack.com {brand}`
3. `"{brand}" affiliate "PPC" OR "paid search" OR "Google Ads"`
4. `"{brand}" affiliate "brand" OR "trademark" keywords bidding`
Nhiều chương trình chạy trên mạng affiliate có điều khoản chung của mạng (ví dụ Dub, Rewardful có mục về paid ads/brand bidding). Nếu tìm được điều khoản chung đó, dùng nó làm kết luận kèm ghi rõ "theo điều khoản chung của {mạng}", độ tin cậy trung bình, thay vì mặc định.

## Đầu ra `_workspace/02_policy_{lô}.md`
```markdown
### example.com
- Cấm bid brand: có/không/không rõ
- Cấm PPC/Google Ads nói chung: có/không/không rõ
- Direct linking: …   Giới hạn quốc gia: …
- Kết luận cột Google Ads: {giá trị chuẩn}
- Trích dẫn: "…nguyên văn…" — https://…
- Độ tin cậy: cao (điều khoản chính chủ) / trung bình (nguồn thứ cấp hoặc điều khoản chung của mạng affiliate) / thấp (không thấy điều khoản)
- Đã tra: (bắt buộc khi kết luận "Chưa xác minh") ≥4 truy vấn đã chạy
```

## Hệ quả theo chế độ
- **scout:** domain "Bị Cấm" bị chuyển sang `rejected_brand_bidding`. Nếu độ tin cậy thấp, báo cáo Telegram phải nói rõ là chưa xác minh được và khuyên người dùng tự đọc điều khoản trước khi chi ngân sách ads.
- **audit/marketplace:** vẫn giữ domain trong bảng, nhưng liệt kê tất cả domain "Bị Cấm" trong khối ⚠️ ở đầu file.
