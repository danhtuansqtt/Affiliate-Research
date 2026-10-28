# Đóng gói thành dist\AffiliateViewer.exe (chạy trên Windows, cần: pip install pyinstaller google-auth certifi)
Set-Location $PSScriptRoot
python -m PyInstaller --noconfirm --onefile --windowed --name AffiliateViewer --add-data "index.html;." app.py
Write-Host "Xong: $PSScriptRoot\dist\AffiliateViewer.exe"
