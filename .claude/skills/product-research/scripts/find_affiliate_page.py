#!/usr/bin/env python3
"""Vào trang chủ của sản phẩm, tìm mục Affiliate / Affiliate Program, mở và in nội dung.

Dùng:  python3 find_affiliate_page.py domain.com [--max-chars 6000]
       python3 find_affiliate_page.py domain.com --link   (chỉ in 1 dòng `LINK: <url đăng ký affiliate>`)

Thứ tự:
  1. Mở trang chủ, gom các link có chữ/đường dẫn chứa affiliate, partner, referral...
     (thường nằm ở menu hoặc chân trang).
  2. Thử thêm các đường dẫn hay gặp: /affiliate, /affiliates, /affiliate-program, /partners...
  3. Mở từng trang affiliate tìm được (kể cả khi chuyển sang Tolt, Dub, Rewardful,
     PartnerStack, CellXpert...), in nội dung chữ, rồi mở tiếp các link điều khoản
     (terms, guidelines, policy) trên trang đó.
  4. Mở thêm trang Pricing và About của trang chủ để lấy Giá bán, Năm ra đời.

Dùng Playwright/Chromium nếu có (đọc được trang render bằng JavaScript như Tolt),
không có thì dùng urllib. Kết quả in ra để researcher/policy-checker đọc và ghi
vào file làm việc; script không tự kết luận số liệu.
"""
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

AFF_WORDS = re.compile(r"affiliat|partner|referr|refer-and-earn|ambassador|become an? (affiliate|partner)|earn with us", re.I)
AFF_PATHS = ["/affiliate", "/affiliates", "/affiliate-program", "/affiliate-programme", "/p/affiliate",
             "/partners", "/partner", "/partner-program", "/partnership", "/referral", "/refer",
             "/ambassador", "/earn"]
TERMS_WORDS = re.compile(r"term|guideline|policy|agreement|rules|faq", re.I)
NETWORKS = re.compile(r"tolt\.io|partners\.dub\.co|getrewardful\.com|rewardful\.com|firstpromoter\.com|"
                      r"partnerstack\.com|impact\.com|cellxpert|promotekit|affiliatly|reditus|"
                      r"linkmink|tapfiliate|refersion|awin|shareasale|flexoffers|trackdesk", re.I)
PRICING_WORDS = re.compile(r"pricing|price|plans", re.I)
ABOUT_WORDS = re.compile(r"about|company|story", re.I)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.text, self._href, self._buf, self._skip = [], [], None, [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self._skip += 1
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._buf = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self._skip:
            self._skip -= 1
        if tag == "a" and self._href:
            self.links.append((self._href, " ".join(self._buf).strip()))
            self._href = None

    def handle_data(self, data):
        if self._skip:
            return
        if data.strip():
            self.text.append(data.strip())
            if self._href is not None:
                self._buf.append(data.strip())


def _fetch_urllib(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.geturl(), r.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        # Site cấu hình chứng chỉ sai (thiếu chuỗi trung gian): vẫn đọc được trang công khai,
        # chỉ dùng để ĐỌC nội dung, không gửi dữ liệu gì.
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        import ssl
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            return r.geturl(), r.read().decode("utf-8", "replace")


_browser = None


def _fetch_browser(url):
    global _browser
    from playwright.sync_api import sync_playwright  # noqa: F401
    if _browser is None:
        pw = sync_playwright().start()
        _browser = pw.chromium.launch()
    page = _browser.new_page(user_agent=UA)
    try:
        page.goto(url, timeout=30000, wait_until="networkidle")
        return page.url, page.content()
    finally:
        page.close()


def fetch(url):
    """Trả (url_cuối, links, text) hoặc (url, None, lỗi)."""
    errors = []
    for fn in (_fetch_browser, _fetch_urllib):
        try:
            final, html = fn(url)
            p = _Links()
            p.feed(html)
            links = [(urllib.parse.urljoin(final, h), t) for h, t in p.links]
            return final, links, "\n".join(p.text)
        except ImportError:
            continue
        except urllib.error.HTTPError as e:
            errors.append(f"HTTP {e.code}")
        except Exception as e:  # noqa: BLE001
            errors.append(f"{type(e).__name__}: {e}"[:160])
    return url, None, " | ".join(errors) or "không mở được"


EVIDENCE = []  # (nhãn, url, text) của mọi trang đã mở, để in TÓM TẮT BẰNG CHỨNG cuối cùng
ADS_RX = re.compile(r"paid (ads?|search|traffic|media|advertis)|\bppc\b|search ads?|google ads|adwords|bing ads|"
                    r"brand(ed)? (keyword|term|bid)|trademark|bid(ding)? on|keyword", re.I)
COOKIE_RX = re.compile(r"cookie|attribution window|\b\d+[- ]days?\b|\b\d+[- ]day (window|cookie)", re.I)
COMM_RX = re.compile(r"\d+(\.\d+)?\s*%|\$\s?\d+|recurring|lifetime|commission", re.I)


def show(title, url, text, max_chars):
    EVIDENCE.append((title, url, text or ""))
    print(f"\n===== {title}: {url} =====")
    print(text[:max_chars] if text else "(trống — trang có thể cần JavaScript/đăng nhập)")


def summary(domain, home, home_ok, aff_from_home):
    print("\n\n########## TÓM TẮT BẰNG CHỨNG ##########")
    print(f"Domain: {domain}")
    print(f"Trang chủ {home}: {'MỞ ĐƯỢC' if home_ok else 'KHÔNG MỞ ĐƯỢC'}")
    print(f"Link Affiliate nằm ngay trên trang chủ/sitemap của {domain}: {'CÓ' if aff_from_home else 'KHÔNG THẤY'}")
    print("Các trang đã đọc:")
    for title, url, text in EVIDENCE:
        print(f"  - {title}: {url} ({len(text)} ký tự)")
    for label, rx in (("QUẢNG CÁO / BRAND BIDDING", ADS_RX), ("COOKIE / THỜI HẠN", COOKIE_RX),
                      ("HOA HỒNG", COMM_RX)):
        print(f"\n[{label}] câu liên quan trong các trang affiliate/điều khoản:")
        n = 0
        for title, url, text in EVIDENCE:
            if not re.match(r"TRANG AFFILIATE|ĐIỀU KHOẢN", title):
                continue
            for sent in re.split(r"(?<=[.!?])\s+|\n", text):
                if 12 < len(sent) < 400 and rx.search(sent):
                    print(f"  ({url.split('//')[-1][:40]}) {sent.strip()}")
                    n += 1
                    if n >= 12:
                        break
            if n >= 12:
                break
        if n == 0:
            print("  (không có câu nào)")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 không in được tiếng Việt
    except Exception:  # noqa: BLE001
        pass
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    max_chars = int(sys.argv[sys.argv.index("--max-chars") + 1]) if "--max-chars" in sys.argv else 6000
    if not args:
        sys.exit(__doc__)
    link_only = "--link" in sys.argv
    domain = re.sub(r"^https?://", "", args[0]).strip("/")
    home = f"https://{domain}"

    final, links, text = fetch(home)
    home_ok = links is not None
    if links is None:
        if not link_only: print(f"TRANG CHỦ KHÔNG MỞ ĐƯỢC: {home} — {text}")
        print("=> Nếu lỗi là EGRESS_BLOCKED/proxy: lý do 'mạng cloud bị chặn'. Nếu 403 từ chính site: 'site chặn truy cập'.")
        links = []
    elif not link_only:
        show("TRANG CHỦ", final, text, 1500)

    aff = [(u, t) for u, t in links if AFF_WORDS.search(u) or AFF_WORDS.search(t) or NETWORKS.search(u)]
    # Link trong menu/chân trang render bằng JS có thể không có trong HTML: tìm thêm trong sitemap.
    for sm in (home + "/sitemap.xml", home + "/sitemap_index.xml"):
        try:
            _, xml = _fetch_urllib(sm)
        except Exception:  # noqa: BLE001
            continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
        for sub in [l for l in locs if l.endswith(".xml")][:5]:
            try:
                locs += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", _fetch_urllib(sub)[1])
            except Exception:  # noqa: BLE001
                pass
        aff += [(l, "(sitemap)") for l in locs if AFF_WORDS.search(urllib.parse.urlparse(l).path)][:10]
        break
    candidates, seen = [], set()
    for u, t in aff + [(home + p, "(đường dẫn hay gặp)") for p in AFF_PATHS]:
        key = u.split("#")[0].rstrip("/")
        if key not in seen:
            seen.add(key)
            candidates.append((u, t))

    aff_keys = {u.split("#")[0].rstrip("/") for u, _ in aff}
    if not link_only:
        print("\n===== LINK AFFILIATE TÌM THẤY TRÊN TRANG CHỦ =====")
        for u, t in aff:
            print(f"- {t or '(không có chữ)'} -> {u}")
    if not aff and not link_only:
        print("(không thấy link affiliate trên trang chủ; thử các đường dẫn hay gặp)")

    opened = 0
    while candidates and opened < 4:
        u, t = candidates.pop(0)
        f2, l2, txt2 = fetch(u)
        if link_only and u.split("#")[0].rstrip("/") in aff_keys and (l2 is None or len(txt2) < 80):
            print("LINK:", u.split("#")[0])  # link do chính site đăng, trang render bằng JS nên không đọc được
            return
        if l2 is not None and t == "(đường dẫn hay gặp)" and                 not urllib.parse.urlparse(f2).path.rstrip("/").endswith(urllib.parse.urlparse(u).path.rstrip("/")):
            continue  # đường dẫn đoán bị chuyển về trang chủ: không có trang affiliate thật
        if l2 is None or len(txt2) < 80:
            if NETWORKS.search(u):
                print(f"\n===== CỔNG AFFILIATE: {u} =====\n(không đọc được nội dung: {txt2 if l2 is None else 'trang trống — thường là form đăng nhập/đăng ký'})")
            continue
        opened += 1
        if link_only:
            # Chế độ --link: chỉ in link đăng ký affiliate (ưu tiên trang apply/join của mạng Dub/Tolt/...).
            signup = next((x for x, y in l2 if NETWORKS.search(x)
                           and re.search(r"apply|join|sign|register|become", x + " " + y, re.I)), None)
            print("LINK:", (signup or f2).split("#")[0])
            return
        show(f"TRANG AFFILIATE ({t})", f2, txt2, max_chars)
        # Nút "Join / Sign up" thường dẫn sang cổng Tolt/Dub/PartnerStack...: mở tiếp.
        for x, y in l2:
            key = x.split("#")[0].rstrip("/")
            if NETWORKS.search(x) and key not in seen:
                seen.add(key)
                candidates.insert(0, (x, f"cổng affiliate: {y}"))
        terms = [(x, y) for x, y in l2 if TERMS_WORDS.search(y) or TERMS_WORDS.search(x)]
        for tu, tt in terms[:3]:
            f3, l3, txt3 = fetch(tu)
            if l3 is not None:
                show(f"ĐIỀU KHOẢN ({tt})", f3, txt3, max_chars)
    if not opened and link_only:
        print("LINK: -")
        return
    if not opened:
        print("\nKHÔNG MỞ ĐƯỢC TRANG AFFILIATE NÀO (có thể cần đăng ký, bị chặn, hoặc không có chương trình).")

    for label, rx in (("PRICING", PRICING_WORDS), ("ABOUT", ABOUT_WORDS)):
        pl = next(((u, t) for u, t in links
                   if "#" not in u and (rx.search(t) or rx.search(urllib.parse.urlparse(u).path))), None)
        if pl is None and label == "PRICING":
            pl = (home + "/pricing", "")
        if pl:
            f4, l4, txt4 = fetch(pl[0])
            if l4 is not None:
                show(label, f4, txt4, 3000)

    summary(domain, home, home_ok, bool(aff))

    if _browser is not None:
        _browser.close()


if __name__ == "__main__":
    main()
