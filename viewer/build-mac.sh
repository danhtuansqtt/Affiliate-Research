#!/usr/bin/env bash
# Đóng gói thành ứng dụng macOS: dist/AffiliateViewer.app (phải chạy TRÊN Mac, không build chéo từ Windows).
# Dùng:  bash viewer/build-mac.sh   rồi kéo dist/AffiliateViewer.app vào Applications.
cd "$(dirname "$0")" || exit 1
VENV="$HOME/.affiliate-viewer-venv"
[ -x "$VENV/bin/python" ] || { python3 -m venv "$VENV" && "$VENV/bin/pip" install -q -r requirements.txt; } || exit 1
"$VENV/bin/pip" install -q pyinstaller || exit 1
"$VENV/bin/python" -m PyInstaller --noconfirm --windowed --name AffiliateViewer --add-data "index.html:." app.py || exit 1
echo "Xong: $(pwd)/dist/AffiliateViewer.app"
