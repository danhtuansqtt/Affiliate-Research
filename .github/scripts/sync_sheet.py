#!/usr/bin/env python3
"""Sync new rows from reported_programs__*.md into a Google Sheet."""
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from google.oauth2.service_account import Credentials

SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
SA_EMAIL = os.environ["GOOGLE_SA_EMAIL"]
SA_KEY = os.environ["GOOGLE_SA_PRIVATE_KEY"]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class _UrllibAuthRequest:
    """Minimal google.auth.transport.Request implementation using urllib.

    Avoids depending on the `requests` package (google.auth.transport.requests
    requires it), which the workflow's `pip install google-auth` does not install.
    """

    def __call__(self, url, method="GET", body=None, headers=None, timeout=None, **kwargs):
        req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return _UrllibAuthResponse(resp.status, resp.read())
        except urllib.error.HTTPError as exc:
            return _UrllibAuthResponse(exc.code, exc.read())


class _UrllibAuthResponse:
    def __init__(self, status, data):
        self.status = status
        self.data = data


def get_access_token():
    info = {
        "type": "service_account",
        "client_email": SA_EMAIL,
        "private_key": SA_KEY,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    creds.refresh(_UrllibAuthRequest())
    return creds.token


def changed_files():
    out = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD", "--", "reported_programs__*.md"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [f for f in out.splitlines() if f.strip()]


def added_rows(path):
    diff = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD", "--", path],
        capture_output=True, text=True, check=True,
    ).stdout
    rows = []
    for line in diff.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        content = line[1:].strip()
        if not content.startswith("|"):
            continue
        cells = [c.strip() for c in content.strip("|").split("|")]
        if len(cells) < 5:
            continue
        if cells[0].lower() == "date" or set(cells[0]) <= {"-"}:
            continue
        rows.append(cells)
    return rows


def topic_from_filename(path):
    m = re.match(r"reported_programs__(.+)\.md$", os.path.basename(path))
    return m.group(1) if m else "unknown"


# Chủ đề có hậu tố "-doi" (routine chạy bằng đội agent) ghi vào tab riêng;
# các chủ đề khác giữ nguyên hành vi cũ: tab đầu tiên của bảng tính.
TEAM_SUFFIX = "-doi"
TEAM_TAB = "Affiliate Research"
HEADER = ["Date", "Topic", "Product", "Domain", "Status", "Note"]


def tab_for_topic(topic):
    return TEAM_TAB if topic.endswith(TEAM_SUFFIX) else None


def _api(token, method, path, payload=None):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url, data=body, method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode()


def ensure_tab(token, title):
    """Tạo tab (kèm dòng tiêu đề) nếu bảng tính chưa có tab tên này."""
    meta = json.loads(_api(token, "GET", "?fields=sheets.properties.title"))
    titles = {s["properties"]["title"] for s in meta.get("sheets", [])}
    if title in titles:
        return
    _api(token, "POST", ":batchUpdate",
         {"requests": [{"addSheet": {"properties": {"title": title}}}]})
    append_rows(token, [HEADER], title)
    print(f"Created tab '{title}' with header row.")


def append_rows(token, values, tab=None):
    rng = f"'{tab}'!A:F" if tab else "A:F"
    path = (
        f"/values/{urllib.parse.quote(rng, safe='')}:append"
        "?valueInputOption=RAW&insertDataOption=INSERT_ROWS"
    )
    return _api(token, "POST", path, {"values": values})


def main():
    files = changed_files()
    if not files:
        print("No reported_programs__*.md changes in this push.")
        return
    rows_by_tab = {}
    for f in files:
        topic = topic_from_filename(f)
        tab = tab_for_topic(topic)
        for cells in added_rows(f):
            date, product, domain, status, note = (cells + [""] * 5)[:5]
            rows_by_tab.setdefault(tab, []).append(
                [date, topic, product, domain, status, note])
    if not rows_by_tab:
        print("No new table rows detected.")
        return
    token = get_access_token()
    for tab, rows in rows_by_tab.items():
        if tab:
            ensure_tab(token, tab)
        result = append_rows(token, rows, tab)
        print(f"Appended {len(rows)} row(s) to {tab or 'default tab'}.")
        print(result)


if __name__ == "__main__":
    main()
