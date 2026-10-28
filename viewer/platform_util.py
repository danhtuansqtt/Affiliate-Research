"""Phần khác nhau giữa Windows, macOS và Linux: thư mục dữ liệu, trình duyệt, cờ ẩn cửa sổ."""
import os
import shutil
import sys

NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW, chỉ có nghĩa trên Windows


def app_dir():
    """Thư mục lưu cấu hình, cache, hồ sơ trình duyệt của app."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "AffiliateViewer")


def find_browser():
    """Đường dẫn Edge/Chrome/Brave/Chromium (dùng cho cửa sổ app và đọc Trustpilot); không có thì trả ''."""
    if sys.platform == "win32":
        bases = [os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", ""), os.environ.get("LOCALAPPDATA", "")]
        for rel in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"):
            for b in bases:
                p = os.path.join(b, rel)
                if b and os.path.isfile(p):
                    return p
        return ""
    if sys.platform == "darwin":
        apps = ["/Applications", os.path.expanduser("~/Applications")]
        for rel in ("Google Chrome.app/Contents/MacOS/Google Chrome",
                    "Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                    "Brave Browser.app/Contents/MacOS/Brave Browser",
                    "Chromium.app/Contents/MacOS/Chromium"):
            for a in apps:
                p = os.path.join(a, rel)
                if os.path.isfile(p):
                    return p
        return ""
    for name in ("google-chrome", "google-chrome-stable", "microsoft-edge", "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    return ""
