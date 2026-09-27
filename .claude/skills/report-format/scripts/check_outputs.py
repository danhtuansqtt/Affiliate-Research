#!/usr/bin/env python3
"""Kiểm tra máy móc các file đầu ra trước khi commit.

Dùng: python3 check_outputs.py FILE [FILE ...]
Tự nhận loại file theo tên:
  latest_report*.md        -> giới hạn Telegram (4000 ký tự), thẻ HTML hợp lệ, '&' đã escape
  reported_programs*.md    -> số cột, status hợp lệ, domain trùng
  audited_products.md      -> số cột, domain trùng
  advertiser-audits/*.md   -> số cột bảng 10 cột
Mọi file: dấu hiệu mất ký tự '$' do shell (vd '/usr/bin/bash.018', '0/tháng').
Mặc định chỉ xét dòng MỚI so với git HEAD (dòng cũ không tính); thêm --all để soát toàn bộ.
Thoát mã 1 nếu có lỗi (ERROR); WARN chỉ để reviewer xem lại.
"""
import subprocess
import os
import re
import sys

STATUSES = {
    "reported", "duplicate_already_reported", "rejected_not_new",
    "rejected_no_affiliate_found", "rejected_not_affiliate_model",
    "rejected_not_applicable", "rejected_brand_bidding",
    "rejected_insufficient_data", "rejected_insufficient_evidence",
    "rejected_unconfirmed_launch_date", "rejected_not_ai_tool",
    "rejected_not_launched_yet", "rejected_discontinued",
    "rejected_duplicate_niche",
}
TG_TAGS = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
           "a", "code", "pre", "blockquote", "tg-spoiler", "span"}
DOLLAR_LOSS = [
    (re.compile(r"/(usr/)?bin/(ba)?sh"), "ERROR", "chuỗi '/usr/bin/bash' — '$0' bị shell thay thế"),
    (re.compile(r"(?<![\d.,$€£¥])\b0/(tháng|năm|seat|user|request|phút|GB)"), "WARN",
     "giá '0/...' — có thể '$' + chữ số đầu đã bị shell nuốt"),
    (re.compile(r"(?<![\d.,$€£¥])\b0 (triệu|tỷ)"), "WARN", "số tiền '0 triệu/tỷ' — nghi mất '$'"),
    (re.compile(r"(?<=[ (~])[.,]\d"), "WARN", "số bắt đầu bằng '.' hoặc ',' (vd ' .05', ',399') — nghi mất '$' + chữ số đầu"),
    (re.compile(r"(ngưỡng|mức) rút tối thiểu 0\b(?![.,]\d)"), "WARN", "ngưỡng rút tối thiểu '0' — nghi mất '$'"),
]

UNIT_NOTE = re.compile(r"(Đơn vị|Don vi|đơn vị tiền tệ)\s*:?\s*[A-Z]{3}", re.I)
PRICE = re.compile(r"\d[\d.,]*\s*/\s*(tháng|thang|năm|nam|tuần|tuan|seat|user|chỗ|GB)")
CURRENCY = re.compile(r"[$€£¥₫]|USD|EUR|GBP|VND|SEK|CHF|AUD|NZD|CAD|SGD|INR")

problems = []
ALL = False


def old_lines(path):
    """Các dòng đã có ở HEAD — bỏ qua khi kiểm tra (trừ khi --all)."""
    if ALL:
        return set()
    try:
        out = subprocess.run(["git", "show", f"HEAD:./{os.path.basename(path)}"],
                             cwd=os.path.dirname(os.path.abspath(path)),
                             capture_output=True, text=True, check=True).stdout
        return set(out.splitlines())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()


def report(level, path, lineno, msg):
    problems.append(level)
    print(f"{level} {path}:{lineno}: {msg}")


def rows(lines):
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            yield i, [c.strip() for c in s.strip("|").split("|")]


def check_table(path, lines, old, key_col=None, status_col=None):
    header = None
    keys = {}
    for i, cells in rows(lines):
        if header is None:
            header = len(cells)
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        is_old = lines[i - 1] in old
        if key_col is not None and len(cells) > key_col and is_old:
            keys.setdefault(cells[key_col].lower(), i)
        if is_old:
            continue
        if len(cells) != header:
            report("ERROR", path, i, f"có {len(cells)} cột, header có {header} (thừa/thiếu '|'?)")
        if status_col is not None and len(cells) > status_col and cells[status_col] not in STATUSES:
            report("ERROR", path, i, f"status lạ '{cells[status_col]}'")
        if key_col is not None and len(cells) > key_col:
            k = cells[key_col].lower()
            if k and not k.startswith("(") and k != "-":
                if k in keys:
                    report("WARN", path, i, f"domain '{k}' đã xuất hiện ở dòng {keys[k]}")
                keys.setdefault(k, i)


BLOCK_LABELS = ["• Tính năng:", "• Giá bán:", "• Hoa hồng affiliate:", "• Google Ads:",
                "• Năm ra đời:", "• Cookie:"]
ADS_VALUES = ("Bị Cấm", "Không Cấm", "Chưa xác minh", "không tìm thấy dữ liệu công khai", "-")
VAGUE = [
    (re.compile(r"[$€£]\s?\d[\d.,]*\s*-\s*[$€£]?\d"), "khoảng giá mơ hồ (vd '$95-$99') — chốt 1 giá trị/gói"),
    (re.compile(r"mâu thuẫn|chưa rõ|chưa xác minh được số liệu", re.I), "ô chứa ghi chú mâu thuẫn/chưa rõ — chốt 1 giá trị, chuyển giải thích sang cột Note"),
]
COOKIE_OK = re.compile(r"^(\d+(\s*\(.+\))?|-|không tìm thấy dữ liệu công khai.*)$")


def check_program_values(path, lines, old):
    """Dòng `reported` (11 cột) phải có 6 cột dữ liệu đã chốt, đúng định dạng mục 2b."""
    for i, cells in rows(lines):
        if lines[i - 1] in old or len(cells) < 11 or cells[3] != "reported":
            continue
        tinh_nang, gia, hoa_hong, ads, nam, cookie = cells[5:11]
        if not ads.startswith(ADS_VALUES):
            report("ERROR", path, i, f"cột Google Ads '{ads[:40]}' không phải giá trị chuẩn (Bị Cấm / Không Cấm / Chưa xác minh)")
        if not COOKIE_OK.match(cookie):
            report("WARN", path, i, f"cột Cookie '{cookie[:40]}' phải là số ngày, vd '30' hoặc '90 (mặc định Dub)'")
        for label, val in (("Giá Bán", gia), ("Hoa Hồng", hoa_hong), ("Năm Ra Đời", nam), ("Tính Năng", tinh_nang)):
            for rx, msg in VAGUE:
                if rx.search(val):
                    report("WARN", path, i, f"cột {label}: {msg}")


def check_telegram(path, text):
    if len(text.strip()) > 4000:
        report("ERROR", path, 0, f"{len(text.strip())} ký tự > 4000 (Telegram sẽ cắt)")
    counts = [text.count(l) for l in BLOCK_LABELS]
    if any(counts) and len(set(counts)) > 1:
        missing = [l for l, c in zip(BLOCK_LABELS, counts) if c < max(counts)]
        report("ERROR", path, 0, f"khối 6 dòng thiếu nhãn {missing} (mỗi chương trình phải đủ 6 dòng)")
    elif not any(counts):
        report("WARN", path, 0, "không thấy khối 6 dòng '• Tính năng: …' — chỉ hợp lệ khi không có chương trình nào được chọn")
    for m in re.finditer(r"</?([a-zA-Z-]+)[^>]*>", text):
        if m.group(1).lower() not in TG_TAGS:
            report("ERROR", path, text[:m.start()].count("\n") + 1, f"thẻ HTML '{m.group(0)}' Telegram không hỗ trợ")
    for m in re.finditer(r"&(?!(amp|lt|gt|quot|#\d+);)", text):
        report("ERROR", path, text[:m.start()].count("\n") + 1, "ký tự '&' chưa escape thành '&amp;'")
    for m in re.finditer(r"<(?![a-zA-Z/])", text):
        report("ERROR", path, text[:m.start()].count("\n") + 1, "ký tự '<' chưa escape thành '&lt;'")


def main(paths):
    global ALL
    if "--all" in paths:
        ALL = True
        paths = [p for p in paths if p != "--all"]
    if not paths:
        print(__doc__)
        return 2
    for path in paths:
        text = open(path, encoding="utf-8").read()
        lines = text.splitlines()
        name = os.path.basename(path)
        old = old_lines(path)
        for i, line in enumerate(lines, 1):
            if line in old:
                continue
            for rx, level, msg in DOLLAR_LOSS:
                if rx.search(line):
                    report(level, path, i, msg + f": …{rx.search(line).group(0)}…")
        if name.startswith("latest_report"):
            check_telegram(path, text)
        elif name.startswith("reported_programs"):
            check_table(path, lines, old, key_col=2, status_col=3)
            check_program_values(path, lines, old)
        elif name == "audited_products.md":
            check_table(path, lines, old, key_col=0)
        elif "advertiser-audits" in path:
            check_table(path, lines, old, key_col=1)
            for i, line in enumerate(lines, 1):
                if line in old or not line.startswith("| ") or "STT" in line:
                    continue
                if PRICE.search(line) and not CURRENCY.search(UNIT_NOTE.sub("", line)):
                    report("WARN", path, i, "có giá dạng 'số/tháng' nhưng cả dòng không có đơn vị tiền tệ — nghi mất '$'")
    errors = problems.count("ERROR")
    print(f"--- {errors} ERROR, {problems.count('WARN')} WARN")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
