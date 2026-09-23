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

Các cụm từ thường gặp trong điều khoản:
- **Cấm:** "may not bid on", "trademark/branded keywords", "brand terms", "no PPC", "paid search is prohibited", "negative keyword".
- **Cho phép:** "Paid ads (Google, Facebook…) are allowed".

## Giá trị chuẩn cho cột Google Ads
Luôn chọn **đúng một** trong các giá trị sau, rồi ghi chi tiết trong ngoặc:

| Tình huống | Giá trị |
|---|---|
| Điều khoản cấm bid brand, hoặc cấm PPC/Google Ads | `Bị Cấm ({phạm vi cấm, ví dụ: cấm bid từ khóa thương hiệu "X" trên PPC; các chiến dịch khác được phép})` |
| Điều khoản ghi rõ là được phép | `Không Cấm ({trích ý chính})` |
| Không tìm thấy điều khoản | `không tìm thấy dữ liệu công khai — mặc định Không Cấm` |

Direct linking và giới hạn quốc gia được ghi thêm trong ngoặc nếu có, vì chúng cũng ảnh hưởng tới việc chạy ads.

## Đầu ra `_workspace/02_policy_{lô}.md`
```markdown
### example.com
- Cấm bid brand: có/không/không rõ
- Cấm PPC/Google Ads nói chung: có/không/không rõ
- Direct linking: …   Giới hạn quốc gia: …
- Kết luận cột Google Ads: {giá trị chuẩn}
- Trích dẫn: "…nguyên văn…" — https://…
- Độ tin cậy: cao (điều khoản chính chủ) / trung bình (nguồn thứ cấp) / thấp (không thấy điều khoản)
```

## Hệ quả theo chế độ
- **scout:** domain "Bị Cấm" bị chuyển sang `rejected_brand_bidding`. Nếu độ tin cậy thấp, báo cáo Telegram phải nói rõ là chưa xác minh được và khuyên người dùng tự đọc điều khoản trước khi chi ngân sách ads.
- **audit/marketplace:** vẫn giữ domain trong bảng, nhưng liệt kê tất cả domain "Bị Cấm" trong khối ⚠️ ở đầu file.
