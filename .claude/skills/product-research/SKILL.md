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
2. **Placeholder có lý do.** Không có dữ liệu thì ghi 1 trong 4 giá trị lý do ở mục 2b skill `report-format` (`chỉ xem sau khi đăng ký (…)`, `site chặn truy cập (…)`, `mạng cloud bị chặn — cần đọc lại {link}`, `không công bố`). Phân biệt đúng 4 trường hợp này là bắt buộc, vì mỗi cái dẫn tới một việc khác nhau cho người dùng.
   Nếu chỉ **một con số** trong ô không xác minh được (các phần khác của ô vẫn có dữ liệu), thay đúng con số đó bằng `[không xác minh được số tiền]`. Với dòng viết không dấu thì dùng `[khong xac minh duoc so tien]`.
3. **Nguồn mâu thuẫn: chốt 1 giá trị, ghi phương án còn lại riêng.** Giá trị của trường lấy theo nguồn ưu tiên cao nhất (chính chủ > mạng affiliate > tổng hợp); phương án còn lại ghi ở dòng `Mâu thuẫn:`, ví dụ `Mâu thuẫn: nguồn tổng hợp ghi 12 tháng recurring + giảm 5% cho khách`. Không để ô chỉ có "chưa xác minh được số liệu duy nhất".
4. **Chương trình chung của mạng affiliate** (ví dụ chính sách mặc định của PartnerStack) phải ghi rõ là "theo chính sách chung {mạng}", để người đọc không hiểu nhầm là điều khoản riêng của thương hiệu.
5. **Viết bằng tiếng Việt**, nhưng giữ nguyên tên riêng, tên gói và thuật ngữ như recurring, cookie, lifetime.
6. **Ký tự tiền tệ.** Ghi `$20/tháng` hoặc `20 USD/tháng`. Luôn ghi file bằng Write hoặc Edit. Nếu buộc phải dùng shell, heredoc phải có dấu nháy (`<<'EOF'`). Heredoc không có nháy từng biến `$20` thành `0` và `$0.018` thành `/usr/bin/bash.018` trong repo này.

## BẮT BUỘC: vào trang chủ, tìm mục Affiliate khi còn thiếu thông tin
Người dùng yêu cầu: nếu bất kỳ ô nào trong 6 thông tin (Tính Năng, Giá Bán, Hoa Hồng Affiliate, Google Ads, Năm Ra Đời, Cookie) còn trống, **phải vào trang chủ của chương trình, tìm mục "Affiliate" / "Affiliate Program" / "Partners" / "Referral" (thường ở menu hoặc chân trang), mở ra đọc hết và cập nhật**. Không được ghi giá trị lý do thiếu khi chưa làm bước này.

1. Chạy script (nó làm hết các bước bên dưới và in nội dung ra):
   ```bash
   python3 .claude/skills/product-research/scripts/find_affiliate_page.py {domain}
   ```
   Script mở trang chủ → gom link Affiliate/Partner/Referral trên trang (cả trong `sitemap.xml`) → thử các đường dẫn hay gặp (`/affiliate`, `/affiliates`, `/p/affiliate`, `/partners`, `/referral`…) → mở trang affiliate → mở tiếp nút "Join/Sign up" sang cổng Tolt, Dub, Rewardful, PartnerStack, CellXpert… → mở các link điều khoản (terms, guidelines, FAQ) → mở trang Pricing và About.
2. Đọc kết quả, lấy từ trang affiliate và trang điều khoản: % hoa hồng, recurring bao nhiêu tháng (vd "first 12 payments" = recurring 12 tháng), số ngày cookie, ngưỡng rút, lịch trả, và mọi câu về paid ads/PPC/brand bidding (chuyển nguyên văn cho policy-checker). Lấy Giá Bán từ Pricing, Năm Ra Đời từ About/changelog/blog đầu tiên/copyright.
3. Nếu script báo trang cổng affiliate trống (trang render bằng JavaScript như Tolt): mở lại bằng Chromium/Playwright trong môi trường nếu có (script tự dùng khi cài sẵn `playwright`), hoặc tìm snippet `site:{slug}.tolt.io`, `site:partners.dub.co/{slug}`. Headline kiểu "Earn 20% on all paid customers" là số liệu chính chủ.
4. Ghi vào file làm việc dòng `Đã mở:` gồm URL trang chủ, URL trang affiliate tìm được (hoặc ghi "không có link affiliate trên trang chủ và sitemap"), URL cổng affiliate và trang điều khoản đã đọc.
5. Chỉ sau bước 1-4 mà ô vẫn trống mới được ghi giá trị lý do: cổng affiliate chỉ có form đăng nhập → `chỉ xem sau khi đăng ký ({mạng}: {link})`; trang chủ trả 403 → `site chặn truy cập (…)`; lỗi `EGRESS_BLOCKED` của sandbox → `mạng cloud bị chặn — cần đọc lại {link}`.

## Tra đủ trước khi bỏ trống
Người dùng cần 6 thông tin **cụ thể** cho mỗi chương trình được giữ lại: Tính Năng, Giá Bán, Hoa Hồng Affiliate, Google Ads (do policy-checker), Năm Ra Đời, Cookie. Chỉ được ghi `không tìm thấy dữ liệu công khai` cho một trường khi đã chạy **ít nhất 3 truy vấn khác nhau** cho riêng trường đó và ghi các truy vấn đã thử vào dòng `Đã tra:` dưới mục domain. Truy vấn gợi ý (thay `{brand}`, `{domain}`, `{slug}`):

| Trường | Truy vấn nên thử theo thứ tự |
|---|---|
| Giá Bán | `site:{domain} pricing` · `"{brand}" pricing plans per month` · `"{brand}" price "per month" 2026` |
| Hoa Hồng | `site:{domain} affiliate` · `site:partners.dub.co {slug}` / `site:tolt.io {brand}` / `site:partnerstack.com {brand}` · `"{brand}" affiliate program commission recurring` |
| Năm Ra Đời | `"{brand}" launch OR launched OR "product hunt"` · `"{brand}" founded` · `"{brand}" seed OR raises` (năm gọi vốn đầu tiên) |
| Cookie | `"{brand}" affiliate cookie days` · `"{brand}" affiliate "cookie" OR "attribution window"` · trang chương trình trên mạng affiliate |

**Nguồn dự phòng khi WebFetch bị chặn** (vẫn đọc được qua snippet WebSearch, nên thử trước khi kết luận thiếu):
- Headline trang đăng ký của mạng affiliate thường ghi sẵn mức hoa hồng, ví dụ trang Tolt của VoiceDash ghi "Earn 20% on all paid customers": `site:{slug}.tolt.io`, `site:partners.dub.co/{slug}`, `site:{slug}.getrewardful.com`, `site:{slug}.firstpromoter.com`, `"{brand}" affiliate site:partnerstack.com`.
- Thư mục affiliate tổng hợp (ghi nhãn `(nguồn phụ)`): `"{brand}" site:referly.so`, `"{brand}" site:affililist.com`, `"{brand}" affiliate commission cookie site:taprefer.com OR site:getlasso.co OR site:openaffiliate.com`.
- Bản tìm kiếm của trang chính chủ: `site:{domain} "affiliate" "%"`, `site:{domain} "cookie"`.

**Xác định đúng lý do khi vẫn thiếu:**
- Trang đăng ký chỉ có form đăng nhập (Tolt `/login`, CellXpert, PartnerStack) → `chỉ xem sau khi đăng ký ({mạng}: {link})`.
- Snippet/tìm kiếm cho thấy site trả 403/chặn quốc gia, hoặc sản phẩm ghi "không nhận khách từ {nước}" → `site chặn truy cập (…)`.
- Lỗi là `EGRESS_BLOCKED`/403 từ proxy của sandbox mà snippet cho thấy trang có nội dung công khai → `mạng cloud bị chặn — cần đọc lại {link}` (đây là lỗi hạ tầng, ghi đúng link để lượt sau/người dùng mở lại).
- Đã tra đủ các nguồn trên mà không nơi nào công bố → `không công bố`.

Nếu chương trình chạy trên mạng affiliate có cookie mặc định công khai (ví dụ Dub 90 ngày) mà không tìm được số riêng của hãng, ghi `90 (mặc định Dub)`, không bỏ trống.

Định dạng giá trị ghi vào file làm việc phải theo đúng mục 2b của skill `report-format`: mỗi trường **một giá trị đã chốt** kèm nhãn tin cậy `(chính chủ)` / `(mạng affiliate)` / `(nguồn phụ)`. Nguồn mâu thuẫn thì vẫn chốt 1 giá trị theo thứ tự ưu tiên chính chủ > mạng affiliate > tổng hợp, rồi ghi phương án còn lại vào dòng `Mâu thuẫn:` riêng, để reporter đưa vào cột Note chứ không nhét vào ô.

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
- Mâu thuẫn: … (bỏ dòng nếu không có)
- Đã mở: URL trang chủ → URL trang affiliate → URL cổng affiliate / điều khoản (bắt buộc với mọi domain được giữ lại)
- Đã tra: (chỉ khi có trường ghi giá trị lý do thiếu) liệt kê ≥3 truy vấn đã thử cho từng trường đó, gồm ít nhất 1 truy vấn nguồn dự phòng
- Nguồn: https://…, https://…
```
