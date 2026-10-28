#!/usr/bin/env bash
# Kiểm tra máy (macOS hoặc Linux) đã đủ để chạy đội agent affiliate chưa. Không tự cài gì, chỉ báo thiếu gì.
# Chạy từ thư mục gốc của repo:  bash scripts/mac-setup.sh
set -u
cd "$(dirname "$0")/.."

ok=0; warn=0
pass() { printf '  [OK]    %s\n' "$1"; }
miss() { printf '  [THIẾU] %s\n' "$1"; ok=1; }
note() { printf '  [LƯU Ý] %s\n' "$1"; warn=1; }

echo "== Công cụ =="
command -v git >/dev/null && pass "git $(git --version | awk '{print $3}')" || miss "git (brew install git)"
command -v python3 >/dev/null && pass "python3 $(python3 --version 2>&1 | awk '{print $2}')" || miss "python3 (brew install python)"
command -v claude >/dev/null && pass "Claude Code (claude)" || miss "Claude Code (cài theo hướng dẫn chính thức)"
command -v gh >/dev/null && pass "gh (GitHub CLI)" || note "gh chưa cài: cần để đăng nhập push (brew install gh, rồi gh auth login)"

echo "== Repo =="
[ -d .claude/skills/affiliate-orchestrator ] && pass "skill affiliate-orchestrator có trong .claude/skills" || miss "thiếu .claude/skills/affiliate-orchestrator: đang đứng sai thư mục hoặc chưa git pull?"
[ -f .github/workflows/telegram-notify.yml ] && pass "workflow telegram-notify còn đủ" || miss "thiếu .github/workflows (kiểm tra git status, đừng commit khi thiếu file)"
git config pull.rebase >/dev/null 2>&1 || { git config pull.rebase true && pass "đã đặt git pull.rebase=true cho repo này"; }
git config user.name >/dev/null 2>&1 && pass "git user.name = $(git config user.name)" || note "chưa đặt git user.name/user.email (git config --global user.name ...)"

echo "== Python =="
python3 -c "import google.auth" 2>/dev/null && pass "google-auth" || note "google-auth chưa có (chỉ cần nếu đọc Google Sheet bằng tay: pip3 install google-auth)"
python3 -c "import playwright" 2>/dev/null && pass "playwright" || note "playwright chưa có (tùy chọn, để đọc trang JavaScript: pip3 install playwright && playwright install chromium)"

echo "== Kiểm tra dữ liệu =="
if command -v python3 >/dev/null && [ -f reported_programs__ai-doi.md ]; then
  python3 .claude/skills/report-format/scripts/check_outputs.py reported_programs__ai-doi.md | tail -1
fi

echo
if [ "$ok" -eq 0 ]; then echo "Sẵn sàng. Mở Claude Code trong thư mục này (lệnh: claude)."; else echo "Còn thiếu mục [THIẾU] ở trên."; fi
exit "$ok"
