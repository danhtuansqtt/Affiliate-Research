#!/usr/bin/env python3
"""Bảo trì Google Sheet thủ công (chạy qua workflow sheets-maintenance).

Chế độ (biến môi trường ACTION):
  inspect      chỉ đọc và in các dòng START_ROW..END_ROW của tab TAB, không sửa gì.
  delete_rows  xóa các dòng START_ROW..END_ROW, nhưng CHỈ KHI mọi dòng trong
               vùng đó trùng hoàn toàn (6 cột A:F) với một dòng nằm phía trên
               trong cùng tab. Có dòng không trùng thì dừng, không xóa gì.
  create_tab   tạo tab TAB kèm dòng tiêu đề (Date | Topic | Product | Domain |
               Status | Note) nếu chưa có; tab đã có thì không làm gì.
  rename_tab   đổi tên tab TAB thành NEW_TAB, giữ nguyên dữ liệu. Dừng nếu TAB
               không tồn tại hoặc NEW_TAB đã có.
"""
import json
import os
import sys
import urllib.parse

from sync_sheet import HEADER, _api, ensure_tab, get_access_token

ACTION = os.environ.get("ACTION", "inspect")
TAB = os.environ["TAB"]
START = int(os.environ.get("START_ROW") or 0)
END = int(os.environ.get("END_ROW") or 0)
NEW_TAB = (os.environ.get("NEW_TAB") or "").strip()


def norm(row):
    return tuple((row + [""] * 6)[:6])


def create_tab():
    token = get_access_token()
    meta = json.loads(_api(token, "GET", "?fields=sheets.properties.title"))
    titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
    if TAB in titles:
        print(f"Tab '{TAB}' đã có sẵn, không làm gì. Các tab hiện có: {titles}")
        return
    ensure_tab(token, TAB)
    meta = json.loads(_api(token, "GET", "?fields=sheets.properties.title"))
    print(f"Các tab hiện có: {[s['properties']['title'] for s in meta['sheets']]}")
    print(f"Dòng tiêu đề: {' | '.join(HEADER)}")


def rename_tab():
    if not NEW_TAB:
        sys.exit("Thiếu tên mới (new_tab).")
    token = get_access_token()
    meta = json.loads(_api(token, "GET", "?fields=sheets.properties(sheetId,title)"))
    by_title = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
    if TAB not in by_title:
        sys.exit(f"Không có tab '{TAB}'. Các tab hiện có: {list(by_title)}")
    if NEW_TAB in by_title:
        sys.exit(f"Đã có tab tên '{NEW_TAB}', không đổi tên. Các tab hiện có: {list(by_title)}")
    _api(token, "POST", ":batchUpdate", {"requests": [{"updateSheetProperties": {
        "properties": {"sheetId": by_title[TAB], "title": NEW_TAB}, "fields": "title"}}]})
    meta = json.loads(_api(token, "GET", "?fields=sheets.properties.title"))
    print(f"Đã đổi tên tab '{TAB}' thành '{NEW_TAB}'.")
    print(f"Các tab hiện có: {[s['properties']['title'] for s in meta['sheets']]}")


def main():
    if ACTION == "create_tab":
        return create_tab()
    if ACTION == "rename_tab":
        return rename_tab()
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
