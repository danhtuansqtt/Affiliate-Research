"""Check VIP: gom tín hiệu "sản phẩm đang hot" từ nguồn công khai (không cần khóa API).

Mỗi hàm trả dict nhỏ; lỗi thì trả {"error": "..."} thay vì ném ngoại lệ để một nguồn hỏng không làm hỏng cả lượt.
Nguồn: Google Trends (30 ngày), Trustpilot (qua Edge ẩn vì trang chặn urllib), Google News (30 và 7 ngày),
Hacker News (30 ngày), tuổi domain (RDAP, dự phòng Wayback).
"""
import http.cookiejar
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

import platform_util as pu

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))
CHECKS = ("trends", "trustpilot", "news", "hn", "age")


def _get(url, headers=None, timeout=25):
    h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    h.update(headers or {})
    with _opener.open(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def clean_name(product, domain):
    """Từ khóa thương hiệu: bỏ phần trong ngoặc / sau dấu gạch; quá dài thì dùng tên miền gốc."""
    n = re.split(r"\s+[–—-]\s+|\s*[(\[]", product or "")[0].strip()
    if not n or len(n) > 40:
        n = (domain or "").split(".")[0]
    return n


def guess_domain(domain, product):
    d = (domain or "").strip().lower()
    if d and d != "-" and "." in d:
        return re.sub(r"^https?://|^www\.|/.*$", "", d)
    m = re.search(r"\b([a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,})\b", (product or "").lower())
    return m.group(1) if m else ""


# ---------------- Google Trends (30 ngày) ----------------
def trends(keyword):
    try:
        _get("https://trends.google.com/trends/?geo=US")  # lấy cookie NID
        req = {"comparisonItem": [{"keyword": keyword, "geo": "", "time": "today 1-m"}], "category": 0, "property": ""}
        q = urllib.parse.urlencode({"hl": "en-US", "tz": "-420", "req": json.dumps(req)})
        raw = _get("https://trends.google.com/trends/api/explore?" + q)
        widgets = json.loads(raw[raw.index("{"):])["widgets"]
        w = next(x for x in widgets if x["id"] == "TIMESERIES")
        q2 = urllib.parse.urlencode({"hl": "en-US", "tz": "-420", "req": json.dumps(w["request"]), "token": w["token"]})
        raw2 = _get("https://trends.google.com/trends/api/widgetdata/multiline?" + q2)
        vals = [int(p["value"][0]) for p in json.loads(raw2[raw2.index("{"):])["default"]["timelineData"]]
        if not vals or max(vals) == 0:
            return {"series": vals, "avg": 0, "change": None}
        half = max(1, len(vals) // 2)
        first, last = sum(vals[:half]) / half, sum(vals[-half:]) / half
        return {"series": vals, "avg": round(sum(vals) / len(vals)),
                "change": None if first == 0 else round((last - first) / first * 100)}
    except urllib.error.HTTPError as e:
        return {"error": f"Google Trends từ chối (HTTP {e.code}), thử lại sau vài phút"}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:140]}


# ---------------- Trustpilot (qua Edge/Chrome ẩn) ----------------
def _browser():
    return pu.find_browser()


def trustpilot(domain):
    if not domain:
        return {"error": "không có domain"}
    br = _browser()
    if not br:
        return {"error": "cần cài Chrome hoặc Edge"}
    try:
        prof = os.path.join(tempfile.gettempdir(), "av_tp_profile")
        out = subprocess.run([br, "--headless=new", "--disable-gpu", "--dump-dom", "--virtual-time-budget=7000",
                              f"--user-data-dir={prof}", f"https://www.trustpilot.com/review/{domain}"],
                             capture_output=True, timeout=60, creationflags=pu.NO_WINDOW).stdout.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:120]}
    if len(out) < 5000:
        return {"error": "Trustpilot không trả trang (bị chặn hoặc hết thời gian)"}
    score = reviews = None
    for blob in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', out, re.S):
        try:
            stack = [json.loads(blob)]
        except ValueError:
            continue
        while stack and score is None:
            d = stack.pop()
            if isinstance(d, dict):
                ar = d.get("aggregateRating")
                if isinstance(ar, dict) and ar.get("ratingValue") is not None:
                    score, reviews = ar["ratingValue"], ar.get("reviewCount") or ar.get("ratingCount")
                stack.extend(d.values())
            elif isinstance(d, list):
                stack.extend(d)
    if score is None:
        return {"found": False}
    return {"found": True, "score": float(score), "reviews": int(str(reviews or 0).replace(",", ""))}


# ---------------- Google News (30 ngày và 7 ngày) ----------------
def _news_count(q, when):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": f'"{q}" when:{when}', "hl": "en-US", "gl": "US", "ceid": "US:en"})
    return _get(url).count("<item>")


def news(keyword):
    try:
        return {"d30": _news_count(keyword, "30d"), "d7": _news_count(keyword, "7d")}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:100]}


# ---------------- Hacker News (30 ngày) ----------------
def hackernews(keyword):
    try:
        since = int(time.time()) - 30 * 86400
        q = urllib.parse.urlencode({"query": f'"{keyword}"', "tags": "story", "numericFilters": f"created_at_i>{since}", "hitsPerPage": 1})
        return {"posts": json.loads(_get("https://hn.algolia.com/api/v1/search?" + q)).get("nbHits", 0)}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:100]}


# ---------------- Tuổi domain ----------------
def domain_age(domain):
    if not domain:
        return {"error": "không có domain"}
    try:
        for ev in json.loads(_get(f"https://rdap.org/domain/{domain}")).get("events", []):
            if ev.get("eventAction") == "registration":
                return {"since": ev["eventDate"][:10], "src": "RDAP"}
    except Exception:  # noqa: BLE001
        pass
    try:
        d = json.loads(_get("https://archive.org/wayback/available?url=" + domain + "&timestamp=19900101"))
        ts = d["archived_snapshots"]["closest"]["timestamp"]
        return {"since": f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}", "src": "Wayback (lần lưu đầu)"}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:100]}


def check(product, domain, which=CHECKS):
    domain = guess_domain(domain, product)
    kw = clean_name(product, domain)
    out = {"keyword": kw, "domain": domain, "at": time.strftime("%Y-%m-%d %H:%M")}
    fns = {"trends": lambda: trends(kw), "trustpilot": lambda: trustpilot(domain), "news": lambda: news(kw),
           "hn": lambda: hackernews(kw), "age": lambda: domain_age(domain)}
    for name in which:
        if name in fns:
            out[name] = fns[name]()
            if name == "trends":
                time.sleep(1.5)  # Google Trends hay chặn khi hỏi dồn dập
    return out


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    r = check(sys.argv[1], sys.argv[2])
    r["trends"].pop("series", None)
    print(json.dumps(r, ensure_ascii=False, indent=1))
