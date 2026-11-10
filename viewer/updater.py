"""Tự cập nhật Affiliate Viewer (macOS) từ GitHub Releases của repo.

Workflow build-mac-dmg đăng AffiliateViewer.dmg lên Release với tag v<số build>. App so số build đang chạy
(file version.txt đóng gói cùng app) với Release mới nhất; khi người dùng bấm "Cập nhật" thì tải DMG, kiểm tra
sha256 (nếu GitHub cung cấp), thay app trong chỗ nó đang nằm rồi mở lại. Lỗi giữa chừng thì app cũ vẫn nguyên.
"""
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import urllib.request

REPO = "danhtuansqtt/Affiliate-Research"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
ASSET = "AffiliateViewer.dmg"
_UA = {"User-Agent": "AffiliateViewer-updater", "Accept": "application/vnd.github+json"}


def current_version(resource):
    try:
        with open(resource("version.txt"), encoding="utf-8") as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def app_bundle():
    """Đường dẫn .app đang chạy, hoặc '' nếu chạy từ mã nguồn / không phải macOS."""
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return ""
    m = re.match(r"(.*?\.app)/Contents/MacOS/", os.path.realpath(sys.executable))
    return m.group(1) if m else ""


def check(resource):
    """{'current': n, 'latest': n, 'available': bool, 'can_install': bool, 'notes': str} hoặc {'error': ...}."""
    cur = current_version(resource)
    try:
        req = urllib.request.Request(API, headers=_UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            rel = json.loads(r.read().decode("utf-8"))
        m = re.fullmatch(r"v(\d+)", rel.get("tag_name", ""))
        if not m:
            return {"current": cur, "available": False}
        latest = int(m.group(1))
        asset = next((a for a in rel.get("assets", []) if a.get("name") == ASSET), None)
        return {"current": cur, "latest": latest, "available": bool(asset) and latest > cur,
                "can_install": bool(app_bundle()), "notes": (rel.get("body") or "")[:400]}
    except Exception as e:  # noqa: BLE001  (mất mạng, hết hạn mức API...: không làm phiền người dùng)
        return {"current": cur, "available": False, "error": str(e)[:120]}


def _download(url, dest, expect_sha=None):
    req = urllib.request.Request(url, headers={"User-Agent": _UA["User-Agent"]})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
    if expect_sha and h.hexdigest() != expect_sha:
        raise RuntimeError("File tải về không khớp mã sha256 của GitHub, đã hủy cập nhật.")


def install():
    """Tải bản mới và dựng script thay app. Trả về đường dẫn script; gọi run_swap() rồi thoát app."""
    bundle = app_bundle()
    if not bundle:
        raise RuntimeError("Chỉ tự cập nhật được khi chạy bản đã cài (.app) trên macOS.")
    parent = os.path.dirname(bundle)
    if not os.access(parent, os.W_OK):
        raise RuntimeError(f"Không có quyền ghi vào {parent}. Hãy kéo app vào thư mục Applications rồi mở lại từ đó.")
    if bundle.startswith("/Volumes/"):
        raise RuntimeError("App đang chạy trực tiếp từ file .dmg. Kéo vào Applications rồi mở lại từ đó.")
    with urllib.request.urlopen(urllib.request.Request(API, headers=_UA), timeout=15) as r:
        rel = json.loads(r.read().decode("utf-8"))
    asset = next((a for a in rel.get("assets", []) if a.get("name") == ASSET), None)
    if not asset:
        raise RuntimeError("Bản phát hành mới chưa có file .dmg.")
    url = asset["browser_download_url"]
    if not url.startswith("https://github.com/" + REPO + "/"):
        raise RuntimeError("Địa chỉ tải không thuộc repo của app, đã hủy.")
    sha = (asset.get("digest") or "").removeprefix("sha256:") or None

    work = tempfile.mkdtemp(prefix="avupdate-")
    dmg = os.path.join(work, ASSET)
    mnt = os.path.join(work, "mnt")
    os.makedirs(mnt)
    _download(url, dmg, sha)
    subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-noverify", "-mountpoint", mnt, dmg],
                   check=True, capture_output=True)
    try:
        src = next((os.path.join(mnt, n) for n in os.listdir(mnt) if n.endswith(".app")), None)
        if not src:
            raise RuntimeError("Không thấy file .app trong .dmg.")
        staged = os.path.join(parent, "." + os.path.basename(bundle) + ".new")
        shutil.rmtree(staged, ignore_errors=True)
        subprocess.run(["ditto", src, staged], check=True, capture_output=True)  # giữ nguyên chữ ký và quyền
        subprocess.run(["xattr", "-dr", "com.apple.quarantine", staged], capture_output=True)
    finally:
        subprocess.run(["hdiutil", "detach", mnt, "-force"], capture_output=True)

    old = os.path.join(parent, "." + os.path.basename(bundle) + ".old")
    q = shlex.quote
    script = os.path.join(work, "swap.sh")
    with open(script, "w", encoding="utf-8") as f:
        f.write(f"""#!/bin/bash
# chờ app cũ thoát hẳn rồi thay bằng bản mới; lỗi thì trả lại bản cũ
while kill -0 {os.getpid()} 2>/dev/null; do sleep 0.3; done
rm -rf {q(old)}
if mv {q(bundle)} {q(old)} && mv {q(staged)} {q(bundle)}; then
  rm -rf {q(old)}
else
  [ -d {q(old)} ] && [ ! -d {q(bundle)} ] && mv {q(old)} {q(bundle)}
  rm -rf {q(staged)}
fi
open {q(bundle)}
rm -rf {q(work)}
""")
    os.chmod(script, 0o700)
    return script


def run_swap(script):
    subprocess.Popen(["/bin/bash", script], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
