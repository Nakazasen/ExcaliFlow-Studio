# ExcaliFlow Studio: Maintenance & Architecture Manual (v0.5.0)

> **Mục tiêu**: Cung cấp tài liệu bảo trì, kiến trúc hệ thống và quy chuẩn kỹ thuật toàn diện cho các nhà phát triển, quản trị viên và AI Coding Agents khi vận hành, mở rộng hoặc kiểm thử ExcaliFlow Studio.

---

## 📌 1. Thông Tin Phiên Bản & Cấu Trúc Gói

- **Phiên bản hiện tại**: `v0.5.0`
- **Tương thích Python**: Python 3.11, 3.12, 3.13 (64-bit)
- **Tập tin phiên bản nguồn**:
  - `VERSION`: `0.5.0`
  - `pyproject.toml`: `version = "0.5.0"`
  - `src/excaliflow/__init__.py`: `__version__ = "0.5.0"`
  - `uv.lock`: `version = "0.5.0"`

---

## 🏛️ 2. Kiến Trúc Hệ Thống (System Architecture)

ExcaliFlow Studio được thiết kế theo triết lý **100% Local-First & Air-Gapped**, hoàn toàn không gửi bất kỳ dữ liệu mã nguồn nào lên đám mây và không phụ thuộc vào kết nối Internet khi render.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXCALIFLOW STUDIO ENGINE                          │
├──────────────────────────┬────────────────────────────┬─────────────────────┤
│   1. Trích Xuất Tri Thức │   2. Xử Lý Đồ Thị & Diff   │  3. Xuất Bản & Web  │
│  - Python AST & Multi-   │  - Graphify Parser & KG    │  - Offline HTML     │
│    Lang (TS/Go/Rust/C#/  │  - Evidence Graph v1       │  - Flowsint 2.5 Atl.│
│    VBA/SQL/YAML/TOML)    │  - Architecture Diff Engine│  - Excalidraw v2    │
│  - Understand Importer   │  - Staleness Validator     │    (Bound Arrows)   │
│  - Workspace Domain Scan │  - Reach BFS & Edge Trace  │  - Share Card & SVG │
└──────────────────────────┴────────────────────────────┴─────────────────────┘
```

**Các module lõi trong `src/excaliflow/`**:
- `cli.py`: Điểm khởi chạy CLI (`--version`, `open`, `atlas`, `ask`, `explain`, `knowledge`, `bridge`, `install`, `doctor`, `targets`, `update`, và fallback tới `scripts/generate_diagram.py`).
- `explorer.py`: Quét AST Python, đa ngôn ngữ (`JS/TS`, `Go`, `Rust`, `Java`, `C#`, `VBA`) và trả lời hỏi đáp nguồn song ngữ (EN/VI) kèm dẫn chứng `file:line`.
- `atlas.py`: Trình tạo Codebase Atlas tương tác offline với bộ lọc module trực tiếp (`#module-search`) và tô sáng luồng import vào/ra (`edge-in`/`edge-out`).
- `domain_graph.py`: Bộ quét tri thức workspace đa định dạng (`.md`, `.csv`, `.json`, `.ini`, `.yaml`, `.toml`, `.sql`, mã nguồn) theo ngân sách tỷ lệ, liên kết `depends_on` nội bộ và xuất scene Excalidraw v2 có binding mũi tên.
- `knowledge.py`: Trình xác thực & nhập đồ thị bằng chứng `rag-trace/v1` $\to$ `evidence-graph/v1` (fail-closed).
- `evidence_atlas.py`: Trình kết xuất Flowsint 2.5 offline (`vi`/`ja`/`en`) với vật lý Thiên hà đồng tâm, lọc theo loại node, zoom theo con trỏ, mini ego-radar và xuất SVG offline.
- `bridge.py` & `bridge_server.py`: Khám phá và chạy proxy Atlas Bridge loopback (`127.0.0.1:8788`, `/health`, `/v1/models`, `/v1/chat/completions` giới hạn 2 MB).
- `installer.py` & `update.py`: Bộ cài đặt skill đa AI host, kiểm tra toàn vẹn `doctor` và kiểm tra phiên bản phát hành.

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

## 🧪 6. Ma Trận Kiểm Thử Tự Động (94 Unit Tests)

Toàn bộ 94 ca kiểm thử tự động được tổ chức trong thư mục [`tests/`](file:///d:/Sandbox/ExcaliFlow%20Studio/tests) với 100% tỷ lệ pass:

| Tệp Kiểm Thử | Số Lượng Test | Nội Dung Kiểm Tra |
| :--- | :---: | :--- |
| [`tests/test_generate_diagram.py`](file:///d:/Sandbox/ExcaliFlow%20Studio/tests/test_generate_diagram.py) | 36 | Fail-closed & staleness, Graphify window, sanitize/escaping, Editorial SVG/typography, Reach tracing, Diff engine, Share card, Git hooks |
| [`tests/test_explorer.py`](file:///d:/Sandbox/ExcaliFlow%20Studio/tests/test_explorer.py) | 27 | AST & đa ngôn ngữ (Python, TS, Go, Rust, Java, C#, VBA), hỏi đáp EN/VI, Codebase Atlas lọc & tô sáng cạnh, Atlas Bridge (`/v1/models`, giới hạn payload) |
| [`tests/test_knowledge.py`](file:///d:/Sandbox/ExcaliFlow%20Studio/tests/test_knowledge.py) | 8 | RAG Trace import fail-closed, Flowsint 2.5 Evidence Atlas (bộ lọc loại node, galaxy, mini-radar, xuất SVG offline, zero cloud egress) |
| [`tests/test_package_entrypoint.py`](file:///d:/Sandbox/ExcaliFlow%20Studio/tests/test_package_entrypoint.py) | 8 | Đồng bộ `VERSION`/`pyproject.toml`/`__init__.py`/`uv.lock`, `--version`, cài đặt skill portable & `doctor_issues` |
| [`tests/test_domain_graph.py`](file:///d:/Sandbox/ExcaliFlow%20Studio/tests/test_domain_graph.py) | 6 | Quét workspace `.md`/`.csv`/`.yaml`/`.toml`/`.sql`/C#/VBA, ngân sách tỷ lệ, cạnh `depends_on`, Excalidraw v2 arrow bindings, `--include` |
| [`tests/test_update.py`](file:///d:/Sandbox/ExcaliFlow%20Studio/tests/test_update.py) | 5 | Kiểm tra manifest GitHub Release, kiểm thử offline & bundle release |
| [`tests/test_windows_setup.py`](file:///d:/Sandbox/ExcaliFlow%20Studio/tests/test_windows_setup.py) | 3 | Cài đặt không tương tác Windows, tạo `.zip` (kèm `docs/`) và `.exe` tự giải nén |
| [`tests/test_release_workflow.py`](file:///d:/Sandbox/ExcaliFlow%20Studio/tests/test_release_workflow.py) | 1 | Kiểm tra hợp đồng workflow phát hành Windows |
| **TỔNG CỘNG** | **94 / 94** | **100% Passed (OK)** |

Lệnh chạy kiểm thử chuẩn:
```powershell
$env:PYTHONPATH = "$PWD/src"; py -3 -m unittest discover -s tests -v
```

---

## 📋 7. Quy Trình Bảo Trì & Phát Hành (Release Checklist)

Khi phát hành phiên bản mới hoặc cập nhật tính năng:
1. [x] Chạy toàn bộ 94 unit tests: `py -3 -m unittest discover -s tests -v`.
2. [x] Nâng số phiên bản đồng bộ tại: `VERSION`, `pyproject.toml`, `src/excaliflow/__init__.py`, `uv.lock`.
3. [x] Cập nhật Bảng điều khiển `SKILL.md` (cả trong repo và đồng bộ qua `excaliflow install --host antigravity`).
4. [x] Cập nhật tài liệu song ngữ `README.md` (EN) và `README_VI.md` (VI).
5. [x] Kiểm tra offline runtime & version: `excaliflow --version` và `excaliflow --offline-check`.
6. [x] Lưu checkpoint vào AgentMemory theo giao thức dự án.
7. [x] Tạo git commit rõ ràng và push mã nguồn lên `origin/main`.
