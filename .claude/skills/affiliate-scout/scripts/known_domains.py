#!/usr/bin/env python3
"""Kiểm tra domain đã có trong lịch sử repo chưa (chống xét trùng).

Dùng: python3 known_domains.py domain1.com domain2.com ...
      python3 known_domains.py --file danh_sach.txt   (mỗi dòng 1 domain)
In ra mỗi domain: NEW hoặc KNOWN kèm file + trạng thái/ngày đã ghi.
"""
import glob
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
HISTORY = ["reported_programs*.md", "audited_products.md"]


def norm(d):
    d = d.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    return d.split("/")[0].strip()


def load():
    seen = {}
    for pat in HISTORY:
        for path in glob.glob(os.path.join(ROOT, pat)):
            name = os.path.basename(path)
            for line in open(path, encoding="utf-8"):
                if not line.startswith("|"):
                    continue
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) < 4 or set(cells[0]) <= {"-"}:
                    continue
                if name.startswith("reported_programs"):
                    dom, info = cells[2], f"{cells[3]} ({cells[0]})"
                else:
                    dom, info = cells[0], f"audited ({cells[2]})"
                for part in re.split(r"[ ,;]+", dom):
                    if "." in part:
                        seen.setdefault(norm(part), []).append(f"{name}: {info}")
    return seen


def main(argv):
    if argv[:1] == ["--file"]:
        argv = [l for l in open(argv[1], encoding="utf-8").read().split() if l]
    if not argv:
        print(__doc__)
        return 2
    seen = load()
    for d in argv:
        n = norm(d)
        hits = seen.get(n)
        print(f"KNOWN {n} -> {'; '.join(hits)}" if hits else f"NEW   {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
