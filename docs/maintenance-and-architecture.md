# ExcaliFlow Studio: Maintenance & Architecture Manual (v0.1.3)

> **Mục tiêu**: Cung cấp tài liệu bảo trì, kiến trúc hệ thống và quy chuẩn kỹ thuật toàn diện cho các nhà phát triển, quản trị viên và AI Coding Agents khi vận hành, mở rộng hoặc kiểm thử ExcaliFlow Studio.

---

## 📌 1. Thông Tin Phiên Bản & Cấu Trúc Gói

- **Phiên bản hiện tại**: `v0.1.3`
- **Tương thích Python**: Python 3.11, 3.12, 3.13 (64-bit)
- **Tập tin phiên bản nguồn**:
  - `VERSION`: `0.1.3`
  - `pyproject.toml`: `version = "0.1.3"`
  - `src/excaliflow/__init__.py`: `__version__ = "0.1.3"`
  - `uv.lock`: `version = "0.1.3"`

---

## 🏛️ 2. Kiến Trúc Hệ Thống (System Architecture)

ExcaliFlow Studio được thiết kế theo triết lý **100% Local-First & Air-Gapped**, hoàn toàn không gửi bất kỳ dữ liệu mã nguồn nào lên đám mây và không phụ thuộc vào kết nối Internet khi render.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXCALIFLOW STUDIO ENGINE                          │
├──────────────────────────┬────────────────────────────┬─────────────────────┤
│   1. Trích Xuất Tri Thức │   2. Xử Lý Đồ Thị & Diff   │  3. Xuất Bản & Web  │
│  - AST Parser (Py/JS/TS) │  - Graphify Parser & KG    │  - Offline HTML     │
│  - Understand Importer   │  - Architecture Diff Engine│  - Native .excali.  │
│  - Source Scanner (Regex)│  - Staleness Validator     │  - 1200x630 Card SVG│
│  - Staleness Timestamp   │  - Reach BFS Traversal     │  - Editorial SVG    │
└──────────────────────────┴────────────────────────────┴─────────────────────┘
```

---

## ⚡ 3. Các Trụ Cột Tính Năng Lõi (Core Features)

### 3.1. Truy Vết Lan Truyền Tương Tác (Interactive Reach Tracing)
- **Cơ chế**: Khi người dùng click vào một node trên giao diện `architecture_viewer.html`, thuật toán Breadth-First Search (BFS) phân tích quan hệ chiều xuôi (`adjOut`) và chiều ngược (`adjIn`).
- **Phân loại hiển thị**:
  - **Node được chọn (`.reach-focused`)**: Viền vàng hổ phách, độ dày nét 3.5px, bóng đổ rực rỡ.
  - **Luồng gọi đến (`.reach-upstream`)**: Viền xanh ngọc (Cyan `#00f5d4`), làm sáng các edge tương ứng (`.reach-highlight-up`).
  - **Luồng phụ thuộc (`.reach-downstream`)**: Viền xanh lá (Emerald `#10b981`), làm sáng các edge tương ứng (`.reach-highlight-down`).
  - **Phần tử ngoài luồng (`.reach-dimmed`)**: Giảm độ mờ còn `opacity: 0.15` để loại bỏ nhiễu thị giác.
- **Thanh thông tin nổi (`#reach-bar`)**: Cung cấp bộ đếm tức thời `X Upstream`, `Y Downstream` và nút `✕ Bỏ chọn`.

### 3.2. Hiệu Ứng Luồng Xung Chuyển Động (Animated Signal Flow)
- Nút bấm **`✨ Luồng`** trên floating toolbar kích hoạt animation CSS `@keyframes signalFlowMotion`.
- Tự động tạo hiệu ứng dòng tín hiệu chạy dọc theo nét đứt của các đường liên kết phụ thuộc, mô phỏng luồng dữ liệu thời gian thực.

### 3.3. Động Cơ So Sánh Độ Lệch Kiến Trúc (Architecture Diff Engine)
- Hàm lõi: `compute_architecture_diff(old_analysis, new_analysis)`
- Cờ CLI: `--diff <target>` (hỗ trợ đường dẫn file JSON, thư mục dự án snapshot, hoặc git ref như `HEAD~1`, `main`).
- Phân loại trực quan:
  - `[+] Added` (`classDef added`): Nền xanh lục nhạt, viền đậm.
  - `[-] Removed` (`classDef removed`): Nền đỏ nhạt, nét đứt rời.
  - `[Δ] Modified` (`classDef modified`): Nền vàng hổ phách, viền cam.
  - `[=] Unchanged` (`classDef unchanged`): Nền xám nhạt, ngữ cảnh hỗ trợ.

### 3.4. Thẻ Ảnh Bìa 1200×630 (README & Social Share Card)
- Hàm: `generate_share_card_file(project_dir, out_path)`
- Cờ CLI: `--share-card <path>`
- Xuất thẻ SVG vector độ phân giải cao 1200×630 với Dark gradient hiện đại, mockup giao diện Panzoom và số liệu thống kê nodes/edges thực tế.

---

## 🛡️ 4. Nguyên Tắc Fail-Closed & Độ Mới Của Đồ Thị (Strict Staleness Protocol)

Khi kích hoạt cờ `--strict`, ExcaliFlow thực hiện kiểm định nghiêm ngặt **100% Fail-Closed**:
1. **Kiểm tra độ mới (Staleness Check)**: So sánh `st_mtime` mới nhất của các tập tin mã nguồn với thời điểm tạo đồ thị.
2. **Khám phá ứng viên dạng danh sách (List-based Candidate Discovery)**: Thư mục `graphify-out/` rỗng sẽ không che khuất `graph.json` ở root.
3. **Đồ thị Understand (.understand*)**: Đồ thị Understand cũ hơn mã nguồn trong chế độ `--strict` bắt buộc dừng ngay (`RuntimeError`).
4. **Hậu kiểm sau khi chạy Graphify**: Ngay cả khi lệnh Graphify trả về `exitcode = 0`, hệ thống vẫn đọc lại timestamp trên đĩa; nếu file đồ thị không thực sự được cập nhật mới hơn mã nguồn, chương trình sẽ lập tức báo lỗi và dừng thực thi, ngăn chặn tuyệt đối việc sử dụng cache lỗi.

---

## 🔄 5. Git Post-Commit Automation Hook

### 5.1. Cơ Chế Hoạt Động
ExcaliFlow sử dụng hook `post-commit` cục bộ trong `.git/hooks/post-commit`:
- **Bước 1**: Nếu có `graphify` trên PATH, tự động chạy `graphify extract "$PWD" --code-only --out "$PWD"`.
- **Bước 2**: Tự động gọi `excaliflow` (hoặc fallback về Python script `scripts/generate_diagram.py`) để render lại `architecture_viewer.html` và `.excalidraw`.
- **Thiết kế file cục bộ**: Không chứa lệnh `git add` và không đưa các file sinh ra vào commit, bảo đảm tính độc lập và sạch sẽ của Git repository.

### 5.2. Cài Đặt & Khôi Phục Hook
```powershell
# Cài đặt hook vào repo hiện tại
excaliflow --install-hook

# Ép buộc cập nhật lại hook ExcaliFlow
excaliflow --install-hook --force-hook
```

---

## 🧪 6. Ma Trận Kiểm Thử Tự Động (64 Unit Tests)

Toàn bộ 64 ca kiểm thử tự động được tổ chức trong [`tests/test_generate_diagram.py`](file:///d:/Sandbox/ExcaliFlow%20Studio/tests/test_generate_diagram.py) với 100% tỷ lệ pass:

| Nhóm Kiểm Thử | Số Lượng Test | Nội Dung Kiểm Tra |
| :--- | :---: | :--- |
| **Fail-Closed & Staleness** | 12 | Phát hiện đồ thị cũ, thư mục rỗng, hậu kiểm sau chạy Graphify, Understand stale check |
| **Sanitize & Label Escaping**| 10 | Thoát ký tự đặc biệt, nháy đơn/kép, dấu so sánh, pipe, từ khóa Mermaid |
| **Editorial Typo & Multiline**| 14 | Ngắt dòng `<tspan>`, tính khoảng cách Y, nhúng `<title>`, cắt ranh giới từ |
| **Editorial Visual Types** | 16 | Wardley Map, Sankey Flow, User Journey, Architecture, KPI, Funnel, Risk |
| **Reach Tracing & Signal Flow**| 4 | Kiểm tra presence của CSS, DOM elements, JS BFS traversal engine |
| **Diff Engine & Share Card** | 4 | Phát hiện Added/Removed/Modified nodes, xuất SVG 1200x630 vector |
| **Git Hooks & CLI Options** | 4 | Cài đặt hook, kiểm tra ghi đè an toàn, CLI argument validation |
| **TỔNG CỘNG** | **64 / 64** | **100% Passed (OK)** |

Lệnh chạy kiểm thử chuẩn:
```powershell
py -3 -m unittest discover -s tests -v
```

---

## 📋 7. Quy Trình Bảo Trì & Phát Hành (Release Checklist)

Khi phát hành phiên bản mới hoặc cập nhật tính năng:
1. [x] Chạy toàn bộ 64 unit tests: `py -3 -m unittest discover -s tests`.
2. [x] Nâng số phiên bản đồng bộ tại: `VERSION`, `pyproject.toml`, `src/excaliflow/__init__.py`, `uv.lock`.
3. [x] Cập nhật Bảng điều khiển `SKILL.md` (cả trong repo và trong cấu hình toàn cục `.gemini/config` / `.codex`).
4. [x] Cập nhật tài liệu song ngữ `README.md` (EN) và `README_VI.md` (VI).
5. [x] Kiểm tra offline runtime: `excaliflow --offline-check`.
6. [x] Lưu checkpoint vào AgentMemory theo giao thức dự án.
7. [x] Tạo git commit rõ ràng và push lên `origin/main`.
