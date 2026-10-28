#!/usr/bin/env bash
# Mở Affiliate Viewer trên macOS/Linux. Bấm đúp trong Finder, hoặc chạy:  bash viewer/run-mac.command
# Lần đầu tự tạo môi trường Python riêng (~/.affiliate-viewer-venv) và cài google-auth, certifi.
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "Chưa có python3. Cài bằng:  brew install python"; read -r -p "Nhấn Enter để đóng..." _; exit 1
fi
VENV="$HOME/.affiliate-viewer-venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo "Lần đầu: đang tạo môi trường Python và cài thư viện..."
  python3 -m venv "$VENV" && "$VENV/bin/pip" install -q -r requirements.txt || { echo "Cài thư viện thất bại."; read -r -p "Nhấn Enter để đóng..." _; exit 1; }
fi
exec "$VENV/bin/python" app.py
