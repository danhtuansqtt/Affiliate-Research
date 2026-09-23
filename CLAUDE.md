# Affiliate-Research

## Harness: Nghiên cứu chương trình affiliate

**Mục tiêu:** Tìm, nghiên cứu và kiểm duyệt các chương trình affiliate có thể chạy Google Ads; ghi báo cáo Telegram, bảng audit và lịch sử đúng định dạng repo.

**Kích hoạt:** Khi được yêu cầu làm việc affiliate (scout hằng ngày, audit advertiser Google Ads Transparency, tóm tắt marketplace, nghiên cứu domain, hoặc sửa/chạy lại các việc đó), dùng skill `affiliate-orchestrator`. Câu hỏi đơn giản về dữ liệu đã có thì trả lời trực tiếp.

**Lịch sử thay đổi:**
| Ngày | Thay đổi | Phạm vi | Lý do |
|------|----------|---------|-------|
| 2026-09-23 | Dựng harness ban đầu: 5 agent (scout, researcher, policy-checker, reporter, reviewer) + 5 skill | toàn bộ | Người dùng yêu cầu dựng harness |
| 2026-09-23 | Thêm hướng dẫn xử lý khi mạng bị chặn (dùng WebSearch) và cách dự phòng khi agent chưa được nạp | product-research, brand-bidding-check, affiliate-orchestrator | Lượt chạy thử: proxy trả 403 với các domain affiliate |
| 2026-09-23 | check_outputs.py: thêm các luật phát hiện mất `$` (số bắt đầu bằng `.`/`,`, ngưỡng rút 0, giá không có đơn vị tiền tệ, bỏ qua ghi chú "Đơn vị: USD") | report-format | Phát hiện 20 dòng hỏng ở 2 file audit mà luật cũ chỉ bắt được một phần |
| 2026-09-23 | Thêm quy ước placeholder `[không xác minh được số tiền]` cho một số tiền đơn lẻ không xác minh được | product-research | Lượt sửa 20 dòng bị mất `$` cần phân biệt với ô thiếu toàn bộ dữ liệu |
