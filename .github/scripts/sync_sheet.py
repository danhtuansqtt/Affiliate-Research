#!/usr/bin/env python3
"""Sync new rows from reported_programs__*.md into a Google Sheet."""
import json
import os
import re
import subprocess
import urllib.error
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


def append_rows(token, values):
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/"
        f"A:F:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS"
    )
    body = json.dumps({"values": values}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode()


def main():
    files = changed_files()
    if not files:
        print("No reported_programs__*.md changes in this push.")
        return
    all_rows = []
    for f in files:
        topic = topic_from_filename(f)
        for cells in added_rows(f):
            date, product, domain, status, note = (cells + [""] * 5)[:5]
            all_rows.append([date, topic, product, domain, status, note])
    if not all_rows:
        print("No new table rows detected.")
        return
    token = get_access_token()
    result = append_rows(token, all_rows)
    print(f"Appended {len(all_rows)} row(s) to sheet.")
    print(result)


if __name__ == "__main__":
    main()
