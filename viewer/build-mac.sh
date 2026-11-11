#!/usr/bin/env bash
# Đóng gói thành ứng dụng macOS: dist/AffiliateViewer.app (phải chạy TRÊN Mac, không build chéo từ Windows).
# Dùng:  bash viewer/build-mac.sh   rồi kéo dist/AffiliateViewer.app vào Applications.
cd "$(dirname "$0")" || exit 1
VENV="$HOME/.affiliate-viewer-venv"
[ -x "$VENV/bin/python" ] || { python3 -m venv "$VENV" && "$VENV/bin/pip" install -q -r requirements.txt; } || exit 1
"$VENV/bin/pip" install -q -r requirements.txt pyinstaller || exit 1
[ -f form.txt ] || : > form.txt   # link Google Form ghi lượt xem (workflow ghi từ secret VIEW_FORM_URL; trống = tắt)
[ -f version.txt ] || echo 0 > version.txt   # số build; workflow ghi số thật trước khi build
"$VENV/bin/python" -m PyInstaller --noconfirm --windowed --name AffiliateViewer --add-data "index.html:." --add-data "version.txt:." --add-data "form.txt:." app.py || exit 1
echo "Xong: $(pwd)/dist/AffiliateViewer.app"
