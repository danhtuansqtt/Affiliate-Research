#!/usr/bin/env python3
"""Bảo trì Google Sheet thủ công (chạy qua workflow sheets-maintenance).

Chế độ (biến môi trường ACTION):
  inspect      chỉ đọc và in các dòng START_ROW..END_ROW của tab TAB, không sửa gì.
  delete_rows  xóa các dòng START_ROW..END_ROW, nhưng CHỈ KHI mọi dòng trong
               vùng đó trùng hoàn toàn (6 cột A:F) với một dòng nằm phía trên
               trong cùng tab. Có dòng không trùng thì dừng, không xóa gì.
"""
import json
import os
import sys
import urllib.parse

from sync_sheet import _api, get_access_token

ACTION = os.environ.get("ACTION", "inspect")
TAB = os.environ["TAB"]
START = int(os.environ["START_ROW"])
END = int(os.environ["END_ROW"])


def norm(row):
    return tuple((row + [""] * 6)[:6])


def main():
    if not (2 <= START <= END) or END - START >= 50:
        sys.exit(f"Vùng dòng không hợp lệ: {START}..{END} (phải 2 <= start <= end, tối đa 50 dòng)")
    token = get_access_token()

    meta = json.loads(_api(token, "GET", "?fields=sheets.properties(sheetId,title)"))
    sheet_id = next((s["properties"]["sheetId"] for s in meta["sheets"]
                     if s["properties"]["title"] == TAB), None)
    if sheet_id is None:
        titles = [s["properties"]["title"] for s in meta["sheets"]]
        sys.exit(f"Không có tab '{TAB}'. Các tab hiện có: {titles}")

    rng = urllib.parse.quote(f"'{TAB}'!A1:F{END}", safe="")
    values = json.loads(_api(token, "GET", f"/values/{rng}")).get("values", [])
    if len(values) < END:
        sys.exit(f"Tab '{TAB}' chỉ có {len(values)} dòng, không tới dòng {END}.")

    above = {}
    for i, row in enumerate(values[:START - 1], 1):
        above.setdefault(norm(row), i)

    print(f"Tab '{TAB}', dòng {START}..{END}:")
    not_dup = []
    for i in range(START, END + 1):
        row = norm(values[i - 1])
        dup_of = above.get(row)
        mark = f"TRÙNG dòng {dup_of}" if dup_of else "KHÔNG trùng"
        print(f"  {i}: {' | '.join(row)}   <- {mark}")
        if not dup_of:
            not_dup.append(i)

    if ACTION == "inspect":
        print("Chế độ inspect: không sửa gì.")
        return
    if ACTION != "delete_rows":
        sys.exit(f"ACTION không hợp lệ: {ACTION}")
    if not_dup:
        sys.exit(f"DỪNG, không xóa gì: các dòng {not_dup} không trùng với dòng nào phía trên.")

    _api(token, "POST", ":batchUpdate", {"requests": [{"deleteDimension": {"range": {
        "sheetId": sheet_id, "dimension": "ROWS",
        "startIndex": START - 1, "endIndex": END}}}]})
    print(f"Đã xóa {END - START + 1} dòng trùng ({START}..{END}) khỏi tab '{TAB}'.")


if __name__ == "__main__":
    main()
