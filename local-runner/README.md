# Chạy đội agent affiliate trên máy tính (Windows)

Thư mục này dùng để chạy scout bằng đội agent **trên máy bạn**, thay cho routine trên cloud. So với cloud, chạy trên máy có mạng không bị chặn, nên agent đọc được trực tiếp trang giá, trang affiliate và điều khoản.

| File | Công dụng |
|---|---|
| `prompts/ai.txt`, `prompts/tai-chinh.txt` | Prompt cho từng chủ đề. Viết bằng tiếng Anh ASCII để tránh lỗi mã hoá trên PowerShell. Báo cáo vẫn ra tiếng Việt theo skill `report-format`. |
| `run-scout.ps1` | Chạy một lượt: `git pull`, gọi `claude -p`, ghi log vào `logs/`. |
| `register-tasks.ps1` | Tạo lịch hằng ngày trong Windows Task Scheduler. Chạy lại với `-Remove` để xoá lịch. |

## Cài đặt một lần

1. Cài **Git**, **Python 3** và **Claude Code**, rồi chạy `claude` một lần để đăng nhập.
2. Clone repo và kiểm tra push được lên GitHub:
   ```powershell
   cd E:\Claude
   git clone https://github.com/danhtuansqtt/Affiliate-Research.git
   cd Affiliate-Research
   git push --dry-run origin master
   ```
3. Chạy thử không gọi Claude:
   ```powershell
   powershell -ExecutionPolicy Bypass -File local-runner\run-scout.ps1 -Topic ai -DryRun
   ```
4. Chạy thật một lượt và theo dõi. Lượt này gửi tin Telegram thật và ghi Sheets thật (tab "Affiliate Research"):
   ```powershell
   powershell -ExecutionPolicy Bypass -File local-runner\run-scout.ps1 -Topic ai
   ```
5. Tạo lịch hằng ngày. Mặc định 08:15 cho AI và 09:15 cho Tài chính, theo giờ của máy:
   ```powershell
   powershell -ExecutionPolicy Bypass -File local-runner\register-tasks.ps1
   ```

## Cần biết
- Máy phải **bật và đang đăng nhập** vào giờ chạy. Nếu máy tắt đúng giờ, task sẽ chạy bù khi máy bật lại.
- Kết quả ghi vào `latest_report__ai-doi.md` và `latest_report__tai-chinh-doi.md`. Telegram và Google Sheets do GitHub Actions gửi như cũ.
- Log nằm trong `local-runner/logs/` và không được commit.
- `run-scout.ps1` cấp cho Claude Code các công cụ Bash, Read, Write, Edit, WebSearch, WebFetch, Agent và Skill ở chế độ `acceptEdits`, vì lượt chạy không có người duyệt. Chỉ chạy trong thư mục repo này.
- Muốn đổi giờ: chạy lại `register-tasks.ps1 -AiTime 07:30 -TaiChinhTime 08:30`.
