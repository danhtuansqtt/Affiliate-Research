# Làm việc trên nhiều máy (Windows và macOS)

Repo này là nơi duy nhất chứa đội agent. Toàn bộ skill và agent nằm trong thư mục `.claude/` của repo, nên **clone repo về máy nào là máy đó có đủ**, không cần cài riêng.

## Cài lần đầu trên MacBook

1. Cài công cụ (Homebrew): `brew install git python gh` rồi cài Claude Code theo hướng dẫn chính thức.
2. Đăng nhập GitHub để được push: `gh auth login` (chọn HTTPS). Repo công khai nên clone không cần đăng nhập, nhưng push thì cần.
3. Clone và kiểm tra:

   ```bash
   git clone https://github.com/danhtuansqtt/Affiliate-Research.git ~/Affiliate-Research
   cd ~/Affiliate-Research
   bash scripts/mac-setup.sh
   ```

4. Mở Claude Code trong thư mục repo (`cd ~/Affiliate-Research && claude`). Các skill `affiliate-orchestrator`, `affiliate-scout`, `product-research`, `brand-bidding-check`, `report-format` tự được nạp. Nói "scout tài chính hôm nay" hoặc "audit advertiser AR…" như trên Windows.

## Quy tắc khi dùng hai máy (và routine cloud)

Ba nơi cùng ghi vào repo: máy Windows, MacBook và 2 routine cloud (mỗi sáng khoảng 02:15 và 03:15 UTC). Để không đè lên nhau:

- **Bắt đầu phiên làm việc:** `git pull --rebase`.
- **Kết thúc:** chỉ `git add` đúng file đã sửa (không dùng `git add -A`), commit, `git pull --rebase`, rồi `git push`.
- Không sửa các dòng cũ trong `reported_programs*.md`. Chỉ thêm dòng mới vào cuối, vì `sheets-sync` chỉ đọc dòng vừa được thêm.
- Workflow `deletion-guard` sẽ báo Telegram nếu một commit xóa hơn 5 file.

## Cập nhật skill

Sửa skill ở máy nào cũng được: commit và push, máy kia chạy `git pull`. Không cần chép tay.

## Những thứ KHÔNG nằm trong repo

| Thứ | Ở đâu | Việc cần làm trên Mac |
|---|---|---|
| File khóa service account Google (`*-sa-key.json`) | Chỉ trên máy | Chỉ cần nếu muốn đọc hoặc sửa Google Sheet bằng tay. Chuyển bằng AirDrop hoặc trình quản lý mật khẩu, cất ngoài thư mục repo, `chmod 600`. Tuyệt đối không commit. |
| Token bot Telegram, khóa Sheet cho GitHub Actions | GitHub Secrets | Không cần gì. Các workflow tự dùng. |
| Bộ nhớ riêng của Claude (memory) | `~/.claude/projects/...` mỗi máy một bản | Không đồng bộ. Điều gì quan trọng thì ghi vào `CLAUDE.md` hoặc skill trong repo. |
| `local-runner/` | Repo | Chỉ dùng cho Windows (PowerShell, hiện đã tắt). Trên Mac không cần. |
| App Affiliate Viewer (`.exe`) | `E:\Claude\affiliate-viewer` | Chỉ chạy Windows. |

## Công cụ tùy chọn

- `pip3 install google-auth`: nếu chạy script đọc Google Sheet trên Mac.
- `pip3 install playwright && playwright install chromium`: để `find_affiliate_page.py` đọc được các trang dựng bằng JavaScript (Tolt…). Không cài thì script tự dùng urllib.

## Kiểm tra nhanh trên bất kỳ máy nào

```bash
python3 .claude/skills/report-format/scripts/check_outputs.py reported_programs__ai-doi.md
```

Kết quả mong đợi: `0 ERROR`.
