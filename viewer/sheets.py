"""Đọc Google Sheet (chỉ đọc) bằng service account, không cần thư viện requests."""
import json
import urllib.error
import urllib.parse
import urllib.request

from google.oauth2.service_account import Credentials

SHEET_ID = ""  # app.py gán từ cấu hình người dùng (không ghi ID vào mã nguồn công khai)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


class _Req:
    def __call__(self, url, method="GET", body=None, headers=None, timeout=None, **kw):
        req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout or 30) as r:
                return _Resp(r.status, r.read())
        except urllib.error.HTTPError as e:
            return _Resp(e.code, e.read())


class _Resp:
    def __init__(self, status, data):
        self.status, self.data = status, data


def token(key_path):
    creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
    creds.refresh(_Req())
    return creds.token


def get(tok, path):
    req = urllib.request.Request(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}{path}",
                                 headers={"Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_all(key_path):
    """Trả {tên_tab: {"header": [...], "rows": [[...]]}} cho mọi tab."""
    tok = token(key_path)
    titles = [s["properties"]["title"] for s in get(tok, "?fields=sheets.properties.title")["sheets"]]
    out = {}
    for t in titles:
        rng = urllib.parse.quote(f"'{t}'", safe="")
        vals = get(tok, f"/values/{rng}?majorDimension=ROWS").get("values", [])
        if not vals:
            continue
        w = len(vals[0])
        out[t] = {"header": vals[0], "rows": [r + [""] * (w - len(r)) for r in vals[1:] if any(c.strip() for c in r)]}
    return out
