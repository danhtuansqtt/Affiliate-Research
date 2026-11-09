#!/usr/bin/env bash
# Đóng gói Affiliate Viewer thành file cài đặt macOS: viewer/dist/AffiliateViewer.dmg
# Phải chạy TRÊN Mac (hdiutil và PyInstaller cho macOS không có trên Windows). Dùng:  bash viewer/build-dmg.sh
# Trên GitHub, workflow build-mac-dmg tự chạy script này trên máy macOS của GitHub.
set -euo pipefail
cd "$(dirname "$0")"
bash build-mac.sh
STAGE="$(mktemp -d)"
cp -R dist/AffiliateViewer.app "$STAGE/"
ln -s /Applications "$STAGE/Applications"   # để kéo ứng dụng vào Applications ngay trong cửa sổ .dmg
rm -f dist/AffiliateViewer.dmg
hdiutil create -volname "Affiliate Viewer" -srcfolder "$STAGE" -ov -format UDZO dist/AffiliateViewer.dmg
rm -rf "$STAGE"
echo "Xong: $(pwd)/dist/AffiliateViewer.dmg"
