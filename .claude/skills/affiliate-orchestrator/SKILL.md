---
name: affiliate-orchestrator
description: "Điều phối đội agent nghiên cứu affiliate của repo Affiliate-Research (scout → researcher + policy-checker song song → reporter → reviewer). Dùng cho MỌI yêu cầu chạy việc affiliate: 'scout hôm nay', 'daily scout', 'scout tài chính', 'tìm chương trình affiliate mới', 'audit/tóm tắt advertiser AR…', 'audit region VN', 'tóm tắt ảnh marketplace PartnerStack', 'nghiên cứu các domain này'. Cả việc tiếp nối: 'chạy lại', 'làm lại phần…', 'bổ sung', 'sửa báo cáo hôm nay', 'cập nhật cột hoa hồng', 'kiểm tra lại brand bidding', 'dựa trên kết quả trước'. Câu hỏi đơn giản về dữ liệu đã có (vd 'domain X đã xét chưa') thì trả lời trực tiếp, không cần chạy cả đội."
---

# Affiliate Orchestrator

Điều phối 5 agent để tạo báo cáo affiliate đúng định dạng repo, đã kiểm duyệt, rồi commit.

## Chế độ thực thi: Subagent
Dùng công cụ `Agent` với `subagent_type` là tên agent trong `.claude/agents/` và **luôn truyền `model: "opus"`**. Chế độ này được chọn thay cho Agent Teams vì hai lý do:
- Các lần chạy định kỳ (routine) diễn ra trong môi trường cloud, nơi chưa bật `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`.
- Các bước ở đây chủ yếu truyền kết quả qua file, không cần các agent tranh luận với nhau.

**Dự phòng:** nếu báo lỗi `Agent type '…' not found` (xảy ra khi agent vừa được tạo trong chính phiên đang chạy, vì agent chỉ nạp lúc mở phiên), hãy gọi `subagent_type: "general-purpose"`. Câu đầu prompt ghi: "Trước tiên đọc `.claude/agents/{tên}.md` và làm đúng vai trò đó."

Nếu sau này bật Agent Teams, có thể gộp researcher và policy-checker thành một team để họ trao đổi trực tiếp khi dữ liệu mâu thuẫn.

## Đội agent

| Agent | Vai trò | Skill | Đầu ra |
|---|---|---|---|
| `scout` | tìm và lọc ứng viên, loại trùng | affiliate-scout | `_workspace/01_scout_candidates.md` |
| `researcher` (N bản) | nghiên cứu các trường dữ liệu | product-research | `_workspace/02_researcher_{lô}.md` |
| `policy-checker` (N bản) | soát brand bidding và Google Ads | brand-bidding-check | `_workspace/02_policy_{lô}.md` |
| `reporter` | viết file đầu ra, nối thêm lịch sử | report-format | các file ở gốc repo + `_workspace/03_reporter_changes.md` |
| `reviewer` | kiểm duyệt PASS/FAIL | report-format, product-research | `_workspace/04_reviewer_verdict.md` |

## Quy trình

### Phase 0: Kiểm tra ngữ cảnh
1. Kiểm tra `_workspace/` có tồn tại không.
   - **Không có**: đây là lần chạy đầu, sang Phase 1.
   - **Có, và người dùng muốn sửa hoặc bổ sung một phần** (ví dụ "kiểm tra lại brand bidding của X", "sửa giá dòng 3"): **chạy lại một phần**. Chỉ gọi lại đúng agent phụ trách, đưa đường dẫn file cũ vào prompt, rồi đi tiếp reporter → reviewer.
   - **Có, và người dùng đưa yêu cầu mới** (chủ đề khác, advertiser khác, ngày mới): **lần chạy mới**. Đổi tên `_workspace/` thành `_workspace_{YYYYMMDD_HHMMSS}/` rồi sang Phase 1.
2. `git pull` nhánh hiện tại. Các routine khác có thể vừa push lịch sử mới, và loại trùng phải dựa trên bản mới nhất.

### Phase 1: Xác định yêu cầu
Xác định **chế độ** và tham số, rồi ghi vào `_workspace/00_input/request.md`:
- `scout`: chủ đề (mặc định AI; `tai-chinh`...), ngày chạy (UTC).
- `audit`: Advertiser ID, region (nếu có), ngày chạy.
- `marketplace`: đường dẫn ảnh hoặc danh sách, tên nguồn (ví dụ PartnerStack).
- `research`: danh sách domain người dùng đưa trực tiếp. Bỏ qua Phase 2 và ghi thẳng `01_scout_candidates.md` với các domain đó ở bảng Giữ lại, sau khi đã loại trùng.

Nếu thiếu tham số bắt buộc (ví dụ audit mà không có ID), hãy hỏi người dùng. Riêng routine không có người theo dõi thì dùng mặc định và ghi lại giả định đã dùng.

### Phase 2: Scout
Gọi `Agent(subagent_type: "scout", model: "opus")` kèm chế độ và tham số. Chờ kết quả, rồi đọc `01_scout_candidates.md`.
- Nếu bảng Giữ lại trống: bỏ qua Phase 3, sang Phase 4. Reporter vẫn phải viết báo cáo "không có ứng viên" và ghi các dòng bị loại vào lịch sử.

### Phase 3: Nghiên cứu song song (fan-out)
1. Chia các domain ở bảng Giữ lại thành lô, mỗi lô **tối đa 8 domain**.
2. Trong **một lượt gọi**, với mỗi lô gọi đồng thời:
   - `Agent(subagent_type: "researcher", model: "opus", run_in_background: true)` → ghi `02_researcher_{lô}.md`
   - `Agent(subagent_type: "policy-checker", model: "opus", run_in_background: true)` → ghi `02_policy_{lô}.md`
3. Giới hạn chung khoảng 10 agent chạy cùng lúc. Lô lớn hơn thì chạy thành nhiều đợt.
4. Chờ tất cả xong. Ở chế độ scout, chuyển các domain "Bị Cấm" hoặc có `ĐỀ XUẤT LOẠI` sang bảng Loại (ghi chú lại trong `01_scout_candidates.md`).
5. Ở chế độ scout, nếu sau bước lọc có nhiều hơn 3 ứng viên đạt, chọn **1–3 cái tốt nhất**. Ưu tiên theo thứ tự: brand bidding được phép rõ ràng, hoa hồng recurring cao, cookie dài, sản phẩm mới hơn. Các ứng viên còn lại ghi `reported` hay loại tùy tiêu chí; khi không chắc thì hỏi người dùng.

### Phase 4: Viết báo cáo
Gọi `Agent(subagent_type: "reporter", model: "opus")` kèm chế độ và danh sách file `_workspace/`.

### Phase 5: Kiểm duyệt (producer–reviewer, tối đa 2 vòng sửa)
1. Gọi `Agent(subagent_type: "reviewer", model: "opus")`.
2. Nếu `04_reviewer_verdict.md` là **FAIL**: gọi lại reporter với danh sách sửa, rồi gọi lại reviewer. Nếu lỗi nằm ở dữ liệu gốc, gọi lại researcher hoặc policy-checker cho đúng domain đó trước khi gọi reporter.
3. Sau 2 vòng mà vẫn FAIL: **không commit**. Báo người dùng các lỗi còn lại và hỏi hướng xử lý. Riêng routine không có người theo dõi: nếu chỉ còn lỗi WARN hoặc nội dung thì commit và nêu rõ trong tin nhắn; nếu còn ERROR của script thì không commit.

### Phase 6: Commit và báo cáo
1. Chạy lại `python3 .claude/skills/report-format/scripts/check_outputs.py` trên các file đã đổi. Chỉ tiếp tục khi không còn ERROR.
2. Tạo **đúng 1 commit** với message theo quy ước trong `report-format`, rồi push ngay.
3. Giữ nguyên `_workspace/` để có thể kiểm tra lại sau. Thư mục này nằm trong `.gitignore`.
4. Tóm tắt cho người dùng: số ứng viên đã xét, được chọn, bị loại, và các cảnh báo còn lại. Sau đó hỏi ngắn: "Có điểm nào trong kết quả hay quy trình muốn chỉnh không?"

## Luồng dữ liệu
```
00_input/request.md → [scout] → 01_scout_candidates.md
        ├─ lô 1 → [researcher] 02_researcher_1.md  +  [policy-checker] 02_policy_1.md
        └─ lô N → …                                    (song song)
→ [reporter] → file ở gốc repo + 03_reporter_changes.md
→ [reviewer] → 04_reviewer_verdict.md ─ FAIL → reporter (≤2 vòng) ─ PASS → commit + push
```

## Xử lý lỗi

| Tình huống | Cách xử lý |
|---|---|
| Một agent lỗi hoặc không trả về kết quả | Gọi lại 1 lần. Lỗi lần nữa thì tiếp tục mà không có phần đó, ghi rõ phần thiếu trong báo cáo. Riêng policy-checker lỗi thì cột Google Ads dùng giá trị mặc định kèm độ tin cậy thấp. |
| Không truy cập được Google Ads Transparency | Dừng chế độ audit và báo người dùng. Không bịa danh sách domain. Nếu người dùng gửi ảnh chụp danh sách creative, có thể đọc từ ảnh (giống chế độ marketplace). |
| Proxy mạng chặn các domain ngoài (403) | Các agent chuyển sang WebSearch (xem product-research). Trong phần tóm tắt, báo người dùng rằng mạng bị chặn và nêu cách sửa: mở phần cài đặt môi trường cloud trên thanh tiêu đề của phiên, chọn Edit, rồi mở rộng Network access hoặc thêm các domain cần dùng. |
| Researcher và policy-checker mâu thuẫn nhau | Giữ cả hai, ghi nguồn của từng bên. Reviewer quyết định cần xác minh lại hay không. |
| Push bị từ chối vì có commit mới trên remote | `git pull --rebase`, chạy lại `known_domains.py` với các domain vừa thêm (một routine khác có thể đã xét chúng), sửa nếu trùng, rồi push. |
| Hơn một nửa số lô thất bại | Dừng và báo người dùng, không commit. |

## Kịch bản kiểm thử

**Luồng bình thường.** Người dùng gõ "scout tài chính hôm nay". Kết quả mong đợi:
1. Phase 1 ghi chế độ scout, chủ đề tai-chinh.
2. Scout xét khoảng 15 ứng viên, giữ lại 4.
3. Phase 3 chạy 1 lô gồm 1 researcher và 1 policy-checker song song.
4. Một domain bị kết luận Bị Cấm và chuyển sang `rejected_brand_bidding`.
5. Reporter viết `latest_report__tai-chinh.md` và nối thêm 15 dòng vào `reported_programs__tai-chinh.md`.
6. Reviewer trả PASS, sau đó tạo 1 commit `scout tai-chinh YYYY-MM-DD` và push.

**Luồng lỗi.** Người dùng gõ "audit AR123… region VN", nhưng researcher ghi `$29/tháng` qua heredoc thành `9/tháng`. Kết quả mong đợi:
1. `check_outputs.py` báo WARN `0/tháng` hoặc ERROR `/usr/bin/bash`.
2. Reviewer trả FAIL, chỉ rõ dòng và ô bị lỗi.
3. Researcher được gọi lại cho domain đó, reporter sửa ô, reviewer trả PASS, rồi commit.
4. Nếu sau 2 vòng vẫn FAIL: không commit, báo người dùng.
