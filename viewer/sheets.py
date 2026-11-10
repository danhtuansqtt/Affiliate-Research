"""Đọc Google Sheet (chỉ đọc) bằng phiên đăng nhập Google của người dùng trong trình duyệt của app.

Tải bản xuất "Trang web (.zip)" của Sheet: mỗi tab là một file .html, ta đọc bảng trong đó.
Cách này dùng đúng quyền xem của tài khoản đã đăng nhập, không cần dự án Google Cloud hay file khóa.
"""
import io
import re
import urllib.error
import urllib.request
import zipfile
from html.parser import HTMLParser

import cdp


class _Redirect(urllib.request.HTTPRedirectHandler):
    """Khi chuyển hướng sang miền khác (vd doc-xx.googleusercontent.com), gắn lại đúng cookie của miền đó."""

    def __init__(self, cookies):
        self.cookies = cookies

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            host = urllib.request.urlparse(newurl).hostname or ""
            new.headers.pop("Cookie", None)
            new.remove_header("Cookie")
            ck = cdp.cookie_header(self.cookies, host)
            if ck:
                new.add_header("Cookie", ck)
        return new


def download_zip(sheet_id, cookies):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=zip"
    req = urllib.request.Request(url, headers={"Cookie": cdp.cookie_header(cookies, "docs.google.com"),
                                                "User-Agent": "Mozilla/5.0"})
    opener = urllib.request.build_opener(_Redirect(cookies))
    try:
        with opener.open(req, timeout=120) as r:
            data = r.read()
            ctype = r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 404):
            raise RuntimeError(f"Google trả lỗi {e.code}: tài khoản đang đăng nhập chưa có quyền xem file này "
                               "(hoặc chủ file tắt quyền tải xuống). Mở file trong cửa sổ Drive để kiểm tra.") from None
        raise
    if "zip" not in ctype and not data.startswith(b"PK"):
        raise RuntimeError("Google không trả file tải xuống (có thể phiên đăng nhập đã hết hạn). Bấm 'Đăng nhập Google' lại.")
    return data


class _Table(HTMLParser):
    """Lấy các hàng của bảng 'waffle' mà Google xuất ra: bỏ hàng tiêu đề chữ cái, cột số dòng, ô freezebar."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self._row, self._cell = [], None, None
        self._in_thead = False

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class", "") or ""
        if tag == "thead":
            self._in_thead = True
        elif tag == "tr" and not self._in_thead:
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = None if "freezebar" in cls else []
            self._skip = "freezebar" in cls
        elif tag == "br" and self._cell is not None:
            self._cell.append("\n")

    def handle_endtag(self, tag):
        if tag == "thead":
            self._in_thead = False
        elif tag == "td" and self._row is not None:
            if self._cell is not None:
                self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(c for c in self._row):
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def parse_zip(data):
    """Trả {tên_tab: {"header": [...], "rows": [[...]]}} như bản đọc bằng API trước đây."""
    out = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if not info.filename.lower().endswith(".html") or "/" in info.filename.strip("/"):
                continue
            name = re.sub(r"\.html$", "", info.filename, flags=re.I)
            p = _Table()
            p.feed(z.read(info).decode("utf-8", "replace"))
            if not p.rows:
                continue
            w = len(p.rows[0])
            out[name] = {"header": p.rows[0], "rows": [r + [""] * (w - len(r)) for r in p.rows[1:]]}
    return out


def fetch_all(sheet_id, cookies):
    return parse_zip(download_zip(sheet_id, cookies))
