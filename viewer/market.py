"""Tín hiệu thị trường cho đánh giá sản phẩm: Google Trends 90 ngày (đọc trực tiếp, không cần khóa hay pandas)
và đường dẫn Trustpilot để kiểm tra thủ công.

Trustpilot chặn truy cập tự động (HTTP 403), nên app KHÔNG tự đọc điểm Trustpilot và không cố vượt cơ chế chống bot của họ:
chỉ đưa đường dẫn vào đánh giá và ghi rõ là chưa đo được để Gemini không coi đó là điểm thấp.
Mỗi hàm không ném ngoại lệ: lỗi thì trả trạng thái dạng chữ để một nguồn hỏng không làm hỏng cả lượt đánh giá.
"""
import http.cookiejar
import json
import re
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36"
_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with _opener.open(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def clean_name(product, domain=""):
    """Từ khóa thương hiệu: bỏ phần trong ngoặc / sau dấu gạch; quá dài thì dùng tên miền gốc."""
    n = re.split(r"\s+[–—-]\s+|\s*[(\[]", product or "")[0].strip()
    if not n or len(n) > 40:
        n = (domain or "").split(".")[0]
    return n


def clean_domain(domain, product=""):
    d = (domain or "").strip().lower()
    if d and d != "-" and "." in d:
        return re.sub(r"^https?://|^www\.|/.*$", "", d)
    m = re.search(r"\b([a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,})\b", (product or "").lower())
    return m.group(1) if m else ""


def trends_url(keyword):
    return "https://trends.google.com.vn/trends/explore?date=today%203-m&q=" + urllib.parse.quote(keyword.strip())


def google_trends(keyword):
    """90 ngày qua, toàn cầu: {'current_score','avg_90d','status','url'}; số liệu là None nếu không đo được."""
    url = trends_url(keyword)
    none = {"current_score": None, "avg_90d": None, "url": url}
    if not keyword.strip():
        return {**none, "status": "Không có từ khóa để tra Google Trends"}
    try:
        _get("https://trends.google.com/trends/?geo=US")  # lấy cookie NID
        req = {"comparisonItem": [{"keyword": keyword, "geo": "", "time": "today 3-m"}], "category": 0, "property": ""}
        q = urllib.parse.urlencode({"hl": "en-US", "tz": "-420", "req": json.dumps(req)})
        raw = _get("https://trends.google.com/trends/api/explore?" + q)
        w = next(x for x in json.loads(raw[raw.index("{"):])["widgets"] if x["id"] == "TIMESERIES")
        q2 = urllib.parse.urlencode({"hl": "en-US", "tz": "-420", "req": json.dumps(w["request"]), "token": w["token"]})
        raw2 = _get("https://trends.google.com/trends/api/widgetdata/multiline?" + q2)
        vals = [int(p["value"][0]) for p in json.loads(raw2[raw2.index("{"):])["default"]["timelineData"]]
    except urllib.error.HTTPError as e:
        return {**none, "status": f"Tạm thời bị giới hạn truy vấn Google Trends (HTTP {e.code}); không đo được"}
    except Exception as e:  # noqa: BLE001
        return {**none, "status": f"Không đo được Google Trends ({type(e).__name__})"}
    if not vals or max(vals) == 0:
        return {"current_score": 0, "avg_90d": 0.0, "url": url, "status": "Chưa đủ dữ liệu tìm kiếm trên Google Trends"}
    mid = len(vals) // 2  # so sánh nửa sau với nửa đầu để biết đà tăng trưởng
    first = sum(vals[:mid]) / max(1, mid)
    second = sum(vals[mid:]) / max(1, len(vals) - mid)
    if first == 0:
        status = "Đang bùng nổ (Breakout)" if second > 10 else "Lưu lượng tìm kiếm thấp"
    else:
        g = (second - first) / first * 100
        status = (f"Đang tăng trưởng mạnh (+{g:.1f}% trong 90 ngày)" if g >= 15 else
                  f"Đang suy giảm ({g:.1f}% trong 90 ngày)" if g <= -15 else f"Giữ nhịp ổn định ({g:+.1f}% trong 90 ngày)")
    return {"current_score": vals[-1], "avg_90d": round(sum(vals) / len(vals), 1), "status": status, "url": url}


def trustpilot_link(domain, product=""):
    d = clean_domain(domain, product)
    url = f"https://www.trustpilot.com/review/{d}" if d else "https://www.trustpilot.com/search?query=" + urllib.parse.quote(clean_name(product))
    return {"rating": None, "reviews": 0, "url": url,
            "status": "CHƯA ĐO ĐƯỢC: Trustpilot chặn truy cập tự động. Đây là thiếu dữ liệu, không phải điểm thấp. Cần kiểm tra thủ công qua link."}


def collect(name, domain):
    """Gom tín hiệu cho một sản phẩm."""
    return {"trends": google_trends(clean_name(name, domain)), "trustpilot": trustpilot_link(domain, name)}
