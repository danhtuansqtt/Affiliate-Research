---
name: product-research
description: "Chuẩn nghiên cứu sản phẩm và chương trình affiliate của repo Affiliate-Research: các trường bắt buộc (tính năng, điểm nổi bật, giá, hoa hồng, link đăng ký, cookie, năm ra đời, điều kiện thanh toán, traffic), cách tìm nguồn, câu placeholder khi thiếu dữ liệu, cách xử lý nguồn mâu thuẫn. Dùng khi tra cứu chi tiết một hay nhiều domain hoặc sản phẩm affiliate, hoặc khi cần bổ sung hay sửa số liệu trong bảng audit."
---

# Product Research — Chuẩn nghiên cứu

## Các trường cần thu thập

| Trường | Nội dung | Nguồn ưu tiên |
|---|---|---|
| Tên Sản Phẩm (Domain) | domain gốc, không có `https://` hay `www.` | — |
| Tính Năng | sản phẩm làm gì, cho ai, các tính năng chính | trang chủ, docs |
| Điểm Nổi Bật | nhà sáng lập, năm thành lập, gọi vốn, số khách hàng, khách hàng lớn, giải thưởng | trang About, Crunchbase, báo chí |
| Giá Bán | từng gói kèm **đơn vị tiền tệ** và chu kỳ; gói free/trial | trang pricing |
| Hoa Hồng Affiliate | %, one-time/recurring, thời hạn (12 tháng/trọn đời), bounty cố định | trang affiliate hoặc mạng affiliate |
| Link Đăng Ký Affiliate | URL đăng ký trực tiếp (trang PartnerStack/Tolt/Impact... của chính chương trình) | trang affiliate |
| Thời Gian Cookie | số ngày, kèm cách ghi nhận (last-click...) nếu có | trang affiliate |
| Năm Ra Đời | năm sản phẩm hoặc công ty ra đời; nếu các nguồn khác nhau thì ghi cả hai | About, Crunchbase, WHOIS |
| (scout) Điều kiện thanh toán | ngưỡng rút tối thiểu, lịch trả, cổng thanh toán, có cần duyệt hồ sơ không | trang affiliate/FAQ |
| (scout) Traffic | ước lượng lượt truy cập/tháng nếu có số liệu công khai | Similarweb/Semrush công khai |

Cột **Google Ads** không thuộc phạm vi skill này. Nó do `brand-bidding-check` quyết định.

## Nguyên tắc dữ liệu
1. **Mỗi con số phải có nguồn.** Ghi dòng `Nguồn:` kèm URL dưới mỗi domain trong file làm việc. Reviewer sẽ mở lại một phần các nguồn này.
2. **Placeholder chuẩn.** Không có dữ liệu thì ghi đúng câu `không tìm thấy dữ liệu công khai`. Có thể thêm lý do ngắn, ví dụ `(chỉ hiện sau khi đăng ký)`. Dùng câu thống nhất giúp người dùng lọc nhanh trên Google Sheets.
   Nếu chỉ **một con số** trong ô không xác minh được (các phần khác của ô vẫn có dữ liệu), thay đúng con số đó bằng `[không xác minh được số tiền]`. Với dòng viết không dấu thì dùng `[khong xac minh duoc so tien]`.
3. **Nguồn mâu thuẫn thì ghi cả hai**, ví dụ: `nguồn A ghi 30% recurring 12 tháng; nguồn B ghi $X/khách — chưa xác minh được số liệu duy nhất`.
4. **Chương trình chung của mạng affiliate** (ví dụ chính sách mặc định của PartnerStack) phải ghi rõ là "theo chính sách chung {mạng}", để người đọc không hiểu nhầm là điều khoản riêng của thương hiệu.
5. **Viết bằng tiếng Việt**, nhưng giữ nguyên tên riêng, tên gói và thuật ngữ như recurring, cookie, lifetime.
6. **Ký tự tiền tệ.** Ghi `$20/tháng` hoặc `20 USD/tháng`. Luôn ghi file bằng Write hoặc Edit. Nếu buộc phải dùng shell, heredoc phải có dấu nháy (`<<'EOF'`). Heredoc không có nháy từng biến `$20` thành `0` và `$0.018` thành `/usr/bin/bash.018` trong repo này.

## Khi mạng bị chặn
Môi trường cloud có thể chặn WebFetch hoặc curl tới các domain bên ngoài (lỗi 403 ở bước CONNECT của proxy). Trong trường hợp đó:
- Chuyển sang **WebSearch giới hạn theo domain chính chủ** (ví dụ `site:thetop.com pricing`). Đây là bản sao trang chính chủ mà công cụ tìm kiếm lưu lại, có giá trị hơn nguồn tổng hợp.
- Ghi `(xác minh qua bản tìm kiếm, chưa mở trực tiếp trang)` ở dòng Nguồn, để reviewer biết cần kiểm tra lại.
- Không coi 403 là "trang không tồn tại".

## Dấu hiệu nên đề xuất loại (ở chế độ scout)
Hãy ghi `ĐỀ XUẤT LOẠI: {status} — {lý do}` ở đầu mục khi gặp một trong các trường hợp:
- sản phẩm ngừng nhận khách mới (`rejected_discontinued`)
- chương trình affiliate mới chỉ "dự kiến" (`rejected_not_affiliate_model`)
- ngày ra mắt sản phẩm sớm hơn tiêu chí (`rejected_not_new`)

## Mẫu một mục trong `_workspace/02_researcher_{lô}.md`
```markdown
### example.com — Example AI
- Tính Năng: …
- Điểm Nổi Bật: …
- Giá Bán: …
- Hoa Hồng Affiliate: …
- Link Đăng Ký Affiliate: …
- Thời Gian Cookie: …
- Năm Ra Đời: …
- Thanh toán / Traffic (scout): …
- Nguồn: https://…, https://…
```
