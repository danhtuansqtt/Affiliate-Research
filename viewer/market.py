"""Tín hiệu thị trường cho đánh giá sản phẩm: Google Trends 90 ngày (đọc trực tiếp, không cần khóa hay pandas)
và đường dẫn Trustpilot để kiểm tra thủ công.

Trustpilot chặn truy cập tự động (HTTP 403), nên app KHÔNG tự đọc điểm Trustpilot và không cố vượt cơ chế chống bot của họ:
chỉ đưa đường dẫn vào đánh giá và ghi rõ là chưa đo được để Gemini không coi đó là điểm thấp.
Mỗi hàm không ném ngoại lệ: lỗi thì trả trạng thái dạng chữ để một nguồn hỏng không làm hỏng cả lượt đánh giá.
"""
import http.cookiejar
import json
import re
import threading
import time
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


# ---------------- Traffic hàng tháng (ước tính từ xếp hạng Tranco) ----------------
# Tranco là bảng xếp hạng độ phổ biến tên miền công khai, miễn phí (tranco-list.eu). Nó chỉ cho THỨ HẠNG, không phải lượt truy cập thật,
# nên traffic hàng tháng được quy ra khoảng theo bậc xếp hạng (có thể lệch vài lần). Số đo thật phải xem ở SimilarWeb (link kèm theo).
_TRAFFIC_BANDS = (  # (thứ hạng tối đa, nhãn, giá trị giữa dùng để sắp xếp)
    (1_000, "trên 100 triệu", 150_000_000),
    (10_000, "15–100 triệu", 40_000_000),
    (50_000, "3–15 triệu", 6_000_000),
    (200_000, "0,7–3 triệu", 1_500_000),
    (1_000_000, "100–700 nghìn", 300_000),
)
_traffic_cache, _traffic_lock, _traffic_last = {}, threading.Lock(), [0.0]


def similarweb_url(domain):
    return f"https://www.similarweb.com/website/{domain}/"


def _band(rank):
    for mx, label, mid in _TRAFFIC_BANDS:
        if rank <= mx:
            return label, mid
    return "dưới 100 nghìn", 50_000


def traffic(domain, product=""):
    """{'rank','label','mid','trend','status','url'}; label/mid là None nếu không đo được. Có bộ nhớ đệm 6 giờ và giãn cách
    giữa các lần gọi vì Tranco giới hạn tần suất (HTTP 429)."""
    d = clean_domain(domain, product)
    if not d:
        return {"rank": None, "label": None, "mid": None, "trend": None, "url": "", "status": "Không có tên miền để tra traffic"}
    now = time.time()
    hit = _traffic_cache.get(d)
    if hit and now - hit[0] < 6 * 3600:
        return hit[1]
    res = {"rank": None, "label": None, "mid": None, "trend": None, "url": similarweb_url(d)}
    with _traffic_lock:
        data = None
        for attempt in range(3):
            wait = 1.6 - (time.time() - _traffic_last[0])
            if wait > 0:
                time.sleep(wait)
            _traffic_last[0] = time.time()
            try:
                req = urllib.request.Request(f"https://tranco-list.eu/api/ranks/domain/{urllib.parse.quote(d)}",
                                             headers={"User-Agent": "AffiliateViewer"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    data = json.loads(r.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 2:
                    time.sleep(3 * (attempt + 1))
                    continue
                res["status"] = f"Tạm thời không tra được xếp hạng (HTTP {e.code}); không đo được traffic"
                return res  # không lưu đệm lỗi
            except Exception as e:  # noqa: BLE001
                res["status"] = f"Không tra được xếp hạng ({type(e).__name__}); không đo được traffic"
                return res
    ranks = [x["rank"] for x in (data or {}).get("ranks", []) if x.get("rank")]
    if not ranks:
        res.update(label="dưới 100 nghìn", mid=50_000, status="Không nằm trong top 1 triệu tên miền của Tranco: traffic ước tính dưới 100 nghìn lượt/tháng (hoặc tên miền quá mới)")
    else:
        rank, oldest = ranks[0], ranks[-1]
        label, mid = _band(rank)
        trend = round((oldest - rank) / oldest * 100, 1) if oldest else None  # dương = thứ hạng tốt lên
        tr = "" if trend is None else (f", thứ hạng tốt lên {trend:.1f}% trong {len(ranks)} ngày" if trend >= 0 else f", thứ hạng xấu đi {abs(trend):.1f}% trong {len(ranks)} ngày")
        res.update(rank=rank, label=label, mid=mid, trend=trend,
                   status=f"Xếp hạng Tranco #{rank:,}{tr}. Traffic ước tính khoảng {label} lượt/tháng (quy từ thứ hạng, có thể lệch vài lần; không phải số đo)")
    _traffic_cache[d] = (now, res)
    return res


def collect(name, domain):
    """Gom tín hiệu cho một sản phẩm."""
    return {"trends": google_trends(clean_name(name, domain)), "trustpilot": trustpilot_link(domain, name),
            "traffic": traffic(domain, name)}
