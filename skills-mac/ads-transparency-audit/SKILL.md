---
name: ads-transparency-audit
description: Từ 1 link Google Ads Transparency Center của một advertiser (hoặc 1 link sản phẩm / ảnh chụp), liệt kê mọi sản phẩm đang quảng cáo trong 30 ngày qua, bỏ domain đã tóm tắt, nghiên cứu 8 trường cho từng domain mới (tính năng, điểm nổi bật, giá, hoa hồng affiliate, link đăng ký, cookie, năm ra đời, Google Ads cấm/không cấm) rồi ghi vào repo GitHub + Google Sheet. Bản dành cho macOS. Kích hoạt khi anh nói "tóm tắt" (không dùng từ "audit").
---

# Skill: Ads Transparency Audit — bản macOS

Bản này là bản gộp của skill gốc trên Windows + các bài học thực tế đến
2026-10-28. Khác biệt chính so với bản Windows: clipboard dùng `pbcopy`, phím
tắt Sheets dùng `cmd`, đường dẫn kiểu Unix, và đã gộp sẵn các cảnh báo / mẹo
trước đây chỉ nằm trong memory.

## 0. Chuẩn bị 1 lần trên Mac

1. `git clone https://github.com/danhtuansqtt/Affiliate-Research.git ~/Affiliate-Research`
   và đăng nhập GitHub (`gh auth login` hoặc credential helper của Git) để push được.
2. Cài/bật **Claude in Chrome** (extension) và đăng nhập Google đang sở hữu Sheet
   "Affiliate Research - Đối soát". Ghi Sheet CHỈ làm được qua Chrome (không có
   API/MCP connector).
3. Python 3 có sẵn trên macOS (hoặc `brew install python`). Thư mục tạm cho
   file trung gian: `mkdir -p /tmp/ads-audit`.
4. Mở trang Ads Transparency Center bằng Browser của Claude (app desktop có
   built-in browser, không cần đăng nhập trang này).

## 1. Khi nào dùng

Anh gửi link `https://adstransparency.google.com/advertiser/AR...` + chữ
**"tóm tắt"**. LUÔN là thao tác thủ công trong phiên, không có routine tự động.

Biến thể:
- **Link sản phẩm / domain / ảnh chụp** (không phải trang advertiser): anh có
  thể nói "bỏ qua check ngày gần nhất" — khi đó KHÔNG kiểm ngày, vào thẳng trang
  chủ từng thương hiệu rồi research. Audit file đặt tên
  `PRODUCT-{domain}__{YYYY-MM-DD}.md` (nhiều thương hiệu cùng lúc:
  `MARKETPLACE-BATCH__{date}.md`), cột Advertiser ID ghi `PRODUCT-LINK` hoặc
  `MARKETPLACE-BATCH`.
- **Advertiser đã tóm tắt trước đây** (cùng AR id): vẫn chạy lại bình thường;
  bước chống trùng sẽ tự loại domain cũ, chỉ domain mới được research.
- Link có sẵn tham số ngày (vd "7 ngày qua"): vẫn dùng cửa sổ 30 ngày chuẩn
  (nói rõ với anh một câu trong chat).

## 2. Đầu ra — CHỈ 2 NƠI, chat chỉ 1-2 câu xác nhận

KHÔNG dán bảng đầy đủ trong chat. Chat chỉ nói: số domain mới, số domain "Bị
Cấm", file repo, Sheet đã cập nhật dòng nào đến dòng nào, và các chỗ dữ liệu
thiếu / suy đoán.

### 2a. Repo GitHub `danhtuansqtt/Affiliate-Research`

- File: `advertiser-audits/{advertiser_id}[_{REGION}]__{YYYY-MM-DD}.md`
  (nếu có region thì thêm `_US`, `_GB`... vd `AR15863532213959131137_US__2026-10-11.md`).
- Cập nhật `audited_products.md` (xem mục 5).
- Mẫu file audit:
  ```
  # Advertiser Audit: {TÊN}

  - Advertiser ID: AR...
  - Region: ...
  - Ngày tóm tắt: YYYY-MM-DD
  - Link: https://adstransparency.google.com/advertiser/AR...?...

  {đoạn thống kê: tổng creative, số còn active ≤30 ngày (từ ngày nào), số domain
  gộp, số domain đã có trong audited_products.md (liệt kê), số domain mới}
  Ghi chú những creative không xác định được domain.

  ⚠️ **N domain cấm Google Ads / PPC**: `d1`, `d2`

  | STT | Tên Sản Phẩm (Domain) | Tính Năng | Điểm Nổi Bật | Giá Bán | Hoa Hồng Affiliate | Link Đăng Ký Affiliate | Thời Gian Cookie | Năm Ra Đời | Google Ads |
  |---|---|---|---|---|---|---|---|---|---|
  ```
  Trong ô không được có ký tự `|` (đổi thành `/`), không xuống dòng.

#### Quy tắc an toàn git (BẮT BUỘC — sự cố thật 2026-10-17 và 2026-10-21)

Hai commit "Add 5StarsDigital…" và "Add LAMBA…" đã lỡ XÓA hàng chục file của repo
(workflow Telegram/Sheets, file audit cũ) vì dùng `git add -A` trên bản sao
cũ/lệch. Đã khôi phục bằng commit `1c5d165` và `7282d14`. Vì vậy:

1. Trước khi tạo file: `git pull --rebase origin master` — nếu báo "unstaged
   changes" thì KHÔNG ép tiếp; xóa bản sao đó và `git clone` mới sang thư mục
   khác rồi làm trên bản mới. Không bao giờ commit từ bản sao cũ.
2. Chỉ `git add` ĐÚNG các file mình tạo/sửa (file audit mới + `audited_products.md`).
   TUYỆT ĐỐI KHÔNG dùng `git add -A`, `git add .`, `git commit -a`.
3. Trước khi commit chạy:
   `git diff --cached --stat` và `git diff --cached --diff-filter=D --name-only`.
   Nếu có BẤT KỲ file bị xóa nào, hoặc hơn 5 file thay đổi ngoài
   `advertiser-audits/` + `audited_products.md` → DỪNG, không commit, báo anh.
4. Commit message kết thúc bằng dòng
   `Co-Authored-By: Claude <noreply@anthropic.com>` (hoặc dòng hệ thống yêu cầu).
5. Push; nếu bị từ chối ("fetch first"): `git pull --rebase origin master` rồi
   push lại. Sau khi push, kiểm tra `.github/workflows/` còn trên `master` và
   `git status -sb` sạch.

### 2b. Google Sheet "Affiliate Research - Đối soát"

Link: `https://docs.google.com/spreadsheets/d/1IMHB8rfG-vN1zezTkBftk2AYszqg5FMRreTy9hU-gmY/edit#gid=103130799`
→ tab **"Advertiser Audit"** (KHÔNG đụng tab "Trang tính1", 6 cột cho skill research).

13 cột, giữ nguyên thứ tự:
`Ngày Tóm Tắt | Advertiser ID | Advertiser Name | STT | Domain | Tính Năng | Điểm Nổi Bật | Giá Bán | Hoa Hồng Affiliate | Link Đăng Ký Affiliate | Thời Gian Cookie | Năm Ra Đời | Google Ads`
(cột E là **domain** thuần, ví dụ `coderabbit.ai` — không phải "Tên (domain)").

Cách nhập (đã kiểm chứng):
1. Ghi toàn bộ dòng (KHÔNG header) ra file `.tsv` UTF-8, tab-separated, đúng 13
   cột/dòng, bằng Python `open(path,'w',encoding='utf-8',newline='\n')`.
   Kiểm tra: `awk -F'\t' '{print NF}' file.tsv | sort | uniq -c` → chỉ ra `13`.
2. Nạp clipboard Mac: `pbcopy < /tmp/ads-audit/rows.tsv`. Kiểm tra ngay trước
   khi dán: `pbpaste | head -c 110` phải thấy đúng dòng đầu. Nếu thao tác khác
   chen vào, nạp lại (clipboard có thể bị ghi đè — đã từng dán nhầm URL vào A465).
3. **LUÔN GHI NỐI TIẾP, KHÔNG BAO GIỜ chèn đầu hay ghi đè.** Tìm dòng cuối thật:
   - Click 1 ô trong cột A (ô dữ liệu), rồi nhấn `cmd+Up` về đầu cột A.
   - Nhấn `cmd+Down` lặp đến khi Hộp tên không đổi nữa / nhảy xuống ô `A1000`
     (hết trang). Sau đó `cmd+Up` 1 lần → dừng ở **dòng dữ liệu cuối cùng**
     (vd `A597`). Nhấn `Down` 1 lần → ô trống đầu tiên (vd `A598`).
   - Đọc Hộp tên (Name Box) để xác nhận; ô đó phải trống.
   - Phím tắt trên Mac có thể khác Windows (Windows dùng `ctrl+Home`,
     `ctrl+Down`); lần đầu chạy, kiểm tra Hộp tên sau mỗi phím trước khi dán.
4. `cmd+v` để dán. Sau khi dán, Google Sheets tự chọn vùng vừa dán: Hộp tên
   hiện `A{đầu}:M{cuối}` và thanh trạng thái "Đếm: N" phải = số dòng × 13. Rồi
   kiểm tra ô ngay dưới dải vừa dán TRỐNG.
5. Đóng tab Chrome đã mở khi xong.

Cảnh báo:
- **Bảng_1**: tab này từng là một Bảng (Table) phạm vi cố định, làm `Ctrl/Cmd+End`
  báo sai và dán đè dữ liệu cũ (sự cố 2026-09-05, phải khôi phục bằng Nhật ký
  phiên bản). Dùng cách `…A1000 → cmd+Up` ở trên thay vì tin `End`. Nếu thấy chip
  "Bảng_1" cạnh A1 thì mở "Điều chỉnh dải ô của bảng" → đặt `A1:M1000`.
- Dán nhầm vào A1 sẽ đè header: nếu xảy ra, `cmd+z` ngay, nạp lại clipboard, dán lại.
- Nếu paste đưa chuỗi lạ (vd chữ địa chỉ ô, URL): `cmd+z`, nạp lại clipboard.
- TUYỆT ĐỐI KHÔNG gõ tay base64 rồi `atob()` để bơm clipboard qua JS (từng làm
  tab thành vertical-tab, lệch cột âm thầm).
- Không gõ địa chỉ vào Hộp tên rồi `cmd+c` ngay (có thể copy ra chữ địa chỉ).
- **Ảnh chụp màn hình bị đơ** (`Page.captureScreenshot timed out`): vẫn dùng
  được phím + `javascript_tool` để đọc Hộp tên:
  `document.getElementById('t-name-box').value` và đếm
  `document.body.innerText.match(/(Đếm|Count)[:\s]*[\d.,]+/)`. Nếu tab đơ hẳn,
  đóng tab, mở tab mới.
- Nếu Claude in Chrome không khả dụng/chưa đăng nhập: báo rõ cho anh, đừng bỏ
  qua âm thầm.

## 3. Quy trình

### 3.1 Nhận link và nạp danh sách chống trùng
`git pull origin master` (trong clone sạch), đọc `audited_products.md` (cột
`Domain | Tên | Ngày tóm tắt đầu tiên | Advertiser ID nguồn`).

### 3.2 Lấy danh sách creative của advertiser (đã bỏ lọc ngày thủ công trên UI)
- **Dùng tham số URL của ATC**: thêm `&preset-date=Last+30+days` vào link
  advertiser (giữ `region=` của link anh gửi). Cách này lọc ổn định và đã chạy
  tốt cho nhiều advertiser, kể cả loại có 750+ creative (chỉ còn ~260 sau lọc).
  KHÔNG dùng dropdown lọc ngày trên UI (không ổn định).
- Đếm creative đã tải:
  `new Set([...document.querySelectorAll('a[href*="/creative/"]')].map(a=>a.href.split('/creative/')[1].split('?')[0])).size`
  — số "~N quảng cáo" hiển thị trên trang chỉ là xấp xỉ.
- Tải hết grid: `window.scrollTo` KHÔNG kích hoạt tải thêm ở một số advertiser.
  Dùng cuộn chuột thật: `computer scroll` (400,400) xuống, amount 10, mỗi 2-3 lần
  cuộn chờ 3-4 giây, rồi đếm lại; lặp đến khi số đếm ổn định (~40 mỗi vòng).
  Phải chụp 1 screenshot sau mỗi lần điều hướng trước khi dùng thao tác tọa độ.
  Gói nhiều thao tác vào `browser_batch` (tối đa ~25 thao tác/lần).
- Lưu `ngày gọi skill` = ngày hiện tại của hệ thống (mốc tính 30 ngày).
- Nếu bộ lọc URL không ăn (số lượng bằng "Mọi lúc"): quay lại cách cũ — mở trang
  creative của mỗi domain và đọc "Lần hiển thị gần đây nhất", giữ ≤30 ngày.

### 3.3 Xác định domain của từng creative
Từ trang grid (đã lọc), phân loại mỗi `a[href*="/creative/"]`:
- **Ảnh `<img src="…tpc.googlesyndication.com/archive/simgad/{N}">`**: mở ảnh
  `https://tpc.googlesyndication.com/archive/simgad/{N}` rồi đọc domain trong ảnh;
  với số lượng lớn, dựng 1 trang lưới các ảnh (đánh số) bằng JS rồi chụp từng
  màn hình để đọc nhanh (xem mục "Mẹo đọc hàng loạt" dưới).
- **Creative HTML / iframe / safeframe / shopping**: gọi RPC
  `POST /anji/_/rpc/LookupService/GetCreativeById?authuser=` với
  `f.req={"1":"AR...","2":"CR...","5":{"1":1,"2":0,"3":2840}}` (url-encoded, content-type
  `application/x-www-form-urlencoded`) trong cùng origin; trong JSON trả về
  `"5"[].1.4` là URL `content.js`. Tham số `overlay=` → URL-decode → base64url-decode
  → gunzip (`DecompressionStream('gzip')`) → đọc `visurl` (domain) và headline.
  Video: mở trang creative, đọc dòng "by {domain}" dưới tiêu đề video; nhiều
  video cùng `obfuscatedCustomerId` thường cùng 1 thương hiệu — chỉ cần kiểm
  vài cái đại diện.
- **Ngày hiển thị gần nhất** (nếu phải kiểm): MAX của `"19"."5"` và mọi
  `"17"[]."5"` trong JSON RPC (`"19"` đơn lẻ đôi khi thấp hơn thực tế).
- Domain không xác định được (banner game "Skip Ads", ATC báo "không thể hiển
  thị quảng cáo này", shopping chỉ có tên cửa hàng…): ghi rõ trong đoạn thống kê
  của file audit; shopping thì tìm domain thật qua web, không tìm được thì ghi
  "Tên (domain chưa xác định)". KHÔNG đoán.
- Quảng cáo đi qua link tracking (vd `go.referralcandy.com` của Govee): gộp về
  domain thương hiệu thật và ghi chú.
- Gom nhóm theo domain; so với `audited_products.md` (so khớp cả domain con /
  domain mẹ, vd `getbrick.us` ≈ `getbrick.com`). Domain đã có → BỎ QUA hoàn toàn.
  Lưu danh sách domain mới ra `/tmp/ads-audit/new_domains.txt`.

### 3.4 Hỏi anh nếu quá nhiều
Nếu >~15 domain mới → dùng `AskUserQuestion` hỏi: "Làm đầy đủ toàn bộ
(Recommended)" / "Chỉ làm N domain đầu" / "Chỉ liệt kê domain". Anh gần như luôn
chọn làm đầy đủ. Nếu 0 domain mới: báo ngắn trong chat, KHÔNG đụng repo/Sheet.

### 3.5 Research 8 trường cho từng domain mới
Với mỗi domain: trang chủ, `/pricing`, `/affiliate`, `/partners`, link footer, mạng
affiliate (PartnerStack, Impact, ShareASale, CJ, Awin, Rewardful, FirstPromoter,
UpPromote, Refersion, GoAffPro, FlexOffers), Crunchbase/LinkedIn cho năm ra đời.
Các trường:
1. **Tính Năng** — làm gì / bán gì.
2. **Điểm Nổi Bật** — 2-4 USP/số liệu.
3. **Giá Bán** — liệt kê hết gói/tier + chu kỳ (hoặc khoảng giá sản phẩm).
4. **Hoa Hồng Affiliate** — %, định kỳ/một lần, các tier.
5. **Link Đăng Ký Affiliate** — URL.
6. **Thời Gian Cookie**.
7. **Năm Ra Đời**.
8. **Google Ads** — điều khoản affiliate có CẤM đấu thầu từ khóa thương hiệu /
   PPC / link trực tiếp không. Nếu cấm: `Bị Cấm — <lý do ngắn + nguồn>`. Nếu cho
   phép hoặc không thấy: `Không Cấm — <ghi chú>` hoặc
   `không tìm thấy dữ liệu công khai — mặc định Không Cấm`. Giá trị CHỈ bắt đầu
   bằng đúng chữ "Bị Cấm" khi thực sự cấm.

**KHÔNG BỊA SỐ LIỆU.** Không có dữ liệu → ghi đúng `không tìm thấy dữ liệu
công khai`. Không có chương trình affiliate → `không có chương trình affiliate
công khai`. Nguồn mâu thuẫn → ghi cả hai số kèm nguồn. Nguồn thứ cấp/chưa xác
minh → ghi chú rõ trong ô. LUÔN liệt kê MỌI sản phẩm đang chạy, kể cả không có
affiliate.

#### Chạy song song bằng subagent (khi >~8 domain)
- Chia domain thành các batch 7-15, mỗi batch 1 subagent `general-purpose` chạy
  nền. Mỗi agent: file input riêng, file output riêng (`resN.tsv`, 9 cột: Tên
  (domain) + 8 trường), tên script helper riêng (đã từng đụng tên `append_row.py`).
- Prompt phải nêu: tiếng Việt, không bịa, không dùng ký tự `|`, tab hay xuống
  dòng trong ô, ghi từng domain ngay khi xong, và **ghi file bằng Python
  `open(path,'a',encoding='utf-8')`** (không dùng `echo/printf` cho tiếng Việt),
  rồi kiểm tra mỗi dòng đủ 9 cột và không mojibake.
- Nếu agent bị HTTP 429 (hết hạn mức phiên): dữ liệu đã ghi từng phần được giữ;
  khi anh bảo "thử lại", chỉ giao lại phần domain CÒN THIẾU (so `resN.tsv` với
  `batchN.txt`).
- Gộp: đọc mọi `res*.tsv`, assert 9 cột, quét mojibake (`Ã`, `â€`, `Ä‘`,
  U+FFFD), đếm "Bị Cấm" bằng `startswith(('bị cấm','bi cam'))` (không đếm "Không
  Cấm"), kiểm tra đủ domain so với danh sách giao.

### 3.6 Dựng file và ghi
1. Dựng file audit `.md` (mẫu mục 2a), file TSV Sheet (13 cột), các dòng
   `audited_products.md`. Cột 2 của audited_products = tên thương hiệu (bỏ
   phần ngoặc domain).
2. Ghi repo (mục 2a, theo quy tắc an toàn git) và Sheet (mục 2b).
3. Chat: 1-2 câu xác nhận + link file repo.

## 4. Chống trùng lặp (`audited_products.md`)

Bảng dùng chung mọi lần chạy: `| domain | Tên | YYYY-MM-DD | AdvertiserID hoặc PRODUCT-LINK hoặc MARKETPLACE-BATCH |`.
- Đầu mỗi lần chạy đọc file; domain đã có → bỏ qua hoàn toàn.
- Cuối lần chạy thêm MỌI domain mới vừa research (không thêm lại domain đã bỏ
  qua; domain bị loại vì quá 30 ngày thì không thêm), ghi nối dưới cùng.
- Domain không xác định được thì ghi dạng `modaven (domain chưa xác định)`.

## 5. Mẹo đọc hàng loạt ảnh quảng cáo (khi >30 ảnh)

Trên tab ATC, dùng `javascript_tool` thay `document.body` bằng 1 `div` cố định
(`position:fixed; overflow-y:scroll; width:1000px; height:600px`) chứa lưới ảnh
`https://tpc.googlesyndication.com/archive/simgad/{N}`, mỗi ô 325px rộng, 70-80px
cao, có nhãn số thứ tự đỏ-vàng ở góc. Cuộn `div.scrollTop` từng đoạn và
screenshot — đọc ~30 ảnh/lần. Nếu screenshot báo timeout, thử lại lần nữa (thường
lần 2 được). Ghi domain theo nhãn số.

## 6. Lưu ý chung

- Tiếng Việt xưng hô "anh/em" khi nói chuyện; trong chat sau khi xong chỉ nói
  ngắn gọn, trung thực: nói rõ phần nào thiếu dữ liệu, suy đoán, lỗi, hoặc bỏ qua.
- Báo cáo thật về các lỗi (mojibake, đè dữ liệu, mất file) — đừng giấu.
- Chỉ chạy thủ công; không tạo routine.
- Dùng chung repo + Sheet với skill `research`; không tạo repo mới.
