"""Ghi nhận lượt xem sản phẩm của từng người dùng (email Google) về một Google Form do quản lý tạo.

Chỉ bật khi có link Form (biến môi trường AV_VIEW_FORM, khóa view_form trong config.json, hoặc file form.txt đóng gói
cùng app). Mỗi dòng gửi gồm: người dùng, sản phẩm, domain; Google Form tự thêm dấu thời gian. Lần gửi lỗi (mất mạng...)
được giữ trong views_pending.jsonl và gửi lại sau.
Link Form: dùng "Lấy đường liên kết điền sẵn" với 3 ô điền đúng USER, PRODUCT, DOMAIN; app đọc mã entry.xxx từ đó.
"""
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

_LOCK = threading.Lock()
_RECENT = {}  # (user, product) -> lúc gửi gần nhất, để một cú click đúp không thành hai dòng
DEBOUNCE = 60


def parse_form(url):
    """Từ link điền sẵn trả (url_gửi, {user|product|domain: 'entry.123'}); None nếu không hợp lệ."""
    url = (url or "").strip()
    m = re.match(r"(https://docs\.google\.com/forms/d/e/[A-Za-z0-9_-]+)/", url)
    if not m:
        return None
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    fields = {}
    for k, v in q.items():
        if k.startswith("entry.") and v and v[0].lower() in ("user", "product", "domain"):
            fields[v[0].lower()] = k
    if len(fields) < 3:
        return None
    return m.group(1) + "/formResponse", fields


def _post(form, rec):
    post_url, fields = form
    data = urllib.parse.urlencode({fields["user"]: rec["user"], fields["product"]: rec["product"],
                                   fields["domain"]: rec["domain"]}).encode("utf-8")
    req = urllib.request.Request(post_url, data=data, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=20) as r:
        if r.status != 200:
            raise RuntimeError(f"Form trả {r.status}")


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]
    except (OSError, ValueError):
        return []


def _write(path, items):
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


def record(pending_path, form, user, product, domain):
    """Xếp một lượt xem vào hàng chờ rồi gửi hết hàng chờ. Trả True nếu đã ghi nhận (không bị bỏ do trùng)."""
    now = time.time()
    key = (user, product)
    with _LOCK:
        if now - _RECENT.get(key, 0) < DEBOUNCE:
            return False
        _RECENT[key] = now
        items = _read(pending_path)
        items.append({"user": user, "product": product, "domain": domain, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        _write(pending_path, items)
    flush(pending_path, form)
    return True


def flush(pending_path, form):
    with _LOCK:
        items = _read(pending_path)
        left = []
        for it in items:
            try:
                _post(form, it)
            except (urllib.error.URLError, OSError, RuntimeError):
                left.append(it)
        _write(pending_path, left)
        return len(left)
