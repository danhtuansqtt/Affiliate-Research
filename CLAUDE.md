# Affiliate-Research

## Harness: Nghiên cứu chương trình affiliate

**Mục tiêu:** Tìm, nghiên cứu và kiểm duyệt các chương trình affiliate có thể chạy Google Ads; ghi báo cáo Telegram, bảng audit và lịch sử đúng định dạng repo.

**Kích hoạt:** Khi được yêu cầu làm việc affiliate (scout hằng ngày, audit advertiser Google Ads Transparency, tóm tắt marketplace, nghiên cứu domain, hoặc sửa/chạy lại các việc đó), dùng skill `affiliate-orchestrator`. Câu hỏi đơn giản về dữ liệu đã có thì trả lời trực tiếp.

**Lịch sử thay đổi:**
| Ngày | Thay đổi | Phạm vi | Lý do |
|------|----------|---------|-------|
| 2026-09-23 | Dựng harness ban đầu: 5 agent (scout, researcher, policy-checker, reporter, reviewer) + 5 skill | toàn bộ | Người dùng yêu cầu dựng harness |
| 2026-09-23 | Thêm hướng dẫn xử lý khi mạng bị chặn (dùng WebSearch) và cách dự phòng khi agent chưa được nạp | product-research, brand-bidding-check, affiliate-orchestrator | Lượt chạy thử: proxy trả 403 với các domain affiliate |
