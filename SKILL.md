---
name: excaliflow
description: "Trung tâm điều khiển trực quan hóa kiến trúc ExcaliFlow Studio: Phân tích codebase/Graphify thành sơ đồ Excalidraw, Codebase Atlas, sơ đồ Editorial (Wardley, Sankey, Journey, Architecture), và Evidence Graph cho RAG."
---

# Excali-Flow Skill: Visual Architecture & Diagramming Protocol (v3.6)

> **MỤC TIÊU CỐT LÕI**: Khi người dùng gõ `/excaliflow` (hoặc gọi skill này mà chưa chỉ định cụ thể tham số phức tạp), Agent **BẮT BUỘC** hiển thị ngay **BẢNG TÍNH NĂNG ĐIỀU KHIỂN (ExcaliFlow Feature Dashboard)** để người dùng chọn nhanh tính năng mong muốn (bằng số hoặc mô tả) thay vì phải tự nhớ lệnh.

---

## 📋 BẢNG TÍNH NĂNG ĐIỀU KHIỂN (ExcaliFlow Feature Dashboard v3.6)

Khi người dùng kích hoạt `/excaliflow`, hãy chào người dùng và hiển thị ngay bảng tính năng sau:

| STT | Nhóm Tính Năng | Mô Tả & Sản Phẩm Đầu Ra | Hành Động CLI / Lệnh Mẫu |
| :---: | :--- | :--- | :--- |
| **1** | 🏢 **Sơ Đồ Kiến Trúc & Excalidraw** | Quét Graphify/AST $\to$ HTML Panzoom (Reach Tracing + Luồng chuyển động) + `.excalidraw` | `excaliflow --dir . --with-excalidraw --open` |
| **2** | 🔍 **So Sánh Kiến Trúc (Diff Mode)** | So sánh độ lệch kiến trúc giữa 2 snapshot hoặc git commit (Added, Removed, Modified) | `excaliflow --diff <file_or_git_ref> --open` |
| **3** | 🎴 **Thẻ Ảnh Bìa 1200×630 (Share Card)**| Xuất ảnh bìa kiến trúc chuẩn 1200×630 dùng cho `README.md` và chia sẻ mạng xã hội | `excaliflow --share-card "README_CARD.svg" --open` |
| **4** | 🗺️ **Codebase Atlas (Học Codebase)** | Giao diện tương tác đọc hiểu codebase, giải thích ứng dụng, đọc sơ đồ SVG native | `excaliflow open --dir .` |
| **5** | 📊 **Editorial & Business Reports** | Xuất SVG/HTML với 11 grammar: architecture, Wardley, Sankey, Journey, KPI, Funnel, Timeline, Process, Quadrant, Matrix, Risk | `excaliflow --editorial-out <out> --visual-type <type>` |
| **6** | 🔍 **Hỏi Đáp Codebase Có Dẫn Chứng** | Phân tích AST và trả lời câu hỏi về hàm/class/import kèm file:line dẫn chứng | `excaliflow ask --dir . --audience engineer --question "..."` |
| **7** | 🔗 **Evidence Graph Cho RAG & Điều Tra** | Chuyển đổi `rag-trace.json` $\to$ Bản đồ tương tác xác minh nguồn trích dẫn | `excaliflow knowledge import` & `atlas` |
| **8** | 🩺 **Atlas AI Bridge Lifecycle** | Khởi tạo/chạy/chẩn đoán Atlas Bridge (`:8788`), AIOS IDE bridge (`:8585`) và Gemini Web2API (`:8081`) | `excaliflow bridge init/start/doctor --dir .` |
| **9** | 📖 **Atlas, Explain & Theo Dõi** | Xuất Atlas/guide, theo dõi source và render lại, kiểm tra tài nguyên offline | `excaliflow atlas`, `explain`, `--watch`, `--offline-check` |
| **10** | 🧩 **Cài Skill Cho AI Host** | Liệt kê target, cài và chẩn đoán skill cho Codex, Claude, Copilot, Gemini, Antigravity và host khác | `excaliflow targets/install/doctor` |
| **11** | 🔄 **Kiểm Tra Bản Cập Nhật** | Kiểm tra phiên bản mới từ GitHub Release của ExcaliFlow-Studio | `excaliflow update check` |

---

## 🛠️ Hướng Dẫn Thực Thi Chi Tiết Từng Nhóm

### Nhóm 1: Sơ Đồ Kiến Trúc Toàn Diện (Kèm Reach Tracing & Luồng Chuyển Động)
- **Mục đích**: Phân tích đồ thị tri thức `graphify-out/graph.json` hoặc AST thành sơ đồ tương tác & bản vẽ Excalidraw.
- **Tương thích Graphify**: Chỉ tự động chạy Graphify trong cửa sổ đã kiểm chứng `>=0.9.48,<0.10`. Bản ngoài cửa sổ phải fallback AST; với `--strict` phải dừng fail-closed thay vì dùng một CLI chưa kiểm chứng.
- **Tính năng tương tác**:
  - **Reach Tracing**: Click vào bất kỳ node nào để cô lập luồng gọi (Upstream) và phụ thuộc (Downstream).
  - **Animated Signal Flow**: Nút `✨ Luồng` trên thanh công cụ kích hoạt dòng chuyển động dữ liệu.
- **Lệnh thực thi**:
  ```powershell
  excaliflow --dir "<project_path>" --with-excalidraw --out "<project_path>\architecture_viewer.html" --open
  ```

### Nhóm 2: So Sánh Kiến Trúc (Architecture Diff Engine)
- **Mục đích**: Phát hiện kiến trúc trôi dạt (drift) trước khi merge PR hoặc giữa 2 bản snapshot.
- **Lệnh thực thi**:
  ```powershell
  excaliflow --dir "<project_path>" --diff "HEAD~1" --open
  # hoặc so sánh với snapshot cũ:
  excaliflow --dir "<project_path>" --diff "old-graph.json" --open
  ```

### Nhóm 3: Thẻ Ảnh Bìa 1200×630 (README Share Card)
- **Mục đích**: Tự động sinh ảnh bìa tỷ lệ chuẩn 1200×630 đính kèm vào đầu `README.md`.
- **Lệnh thực thi**:
  ```powershell
  excaliflow --dir "<project_path>" --share-card "README_CARD.svg" --open
  ```

### Nhóm 4: Codebase Atlas (Khám Phá & Học Code Cho Người Mới)
- **Mục đích**: Tạo trang web giải thích ứng dụng làm gì, 1-2-3 reading path, trách nhiệm từng module.
- **Lệnh thực thi**:
  ```powershell
  excaliflow open --dir "<project_path>"
  ```

### Nhóm 5: Sơ Đồ Xuất Bản Editorial (Slide 16:9, Báo Cáo, Sách Trắng)
- **Mục đích**: Vẽ các sơ đồ trừu tượng chất lượng cao, không phụ thuộc font mạng.
- **Các loại sơ đồ hỗ trợ (`--visual-type`)**:
  1. `architecture`: Sơ đồ kiến trúc tối giản cho slide thuyết trình.
  2. `wardley`: Bản đồ tiến hóa công nghệ (Genesis $\to$ Custom $\to$ Product $\to$ Commodity) kèm chuỗi giá trị.
  3. `sankey`: Biểu đồ dòng chảy dữ liệu / luân chuyển giá trị giữa các node.
  4. `journey`: Bản đồ trải nghiệm người dùng / các giai đoạn phát triển theo thời gian.
  5. `kpi`, `funnel`, `timeline`, `process`, `quadrant`, `matrix`, `risk`: Các báo cáo kinh doanh và vận hành.
- **Lệnh thực thi**:
  ```powershell
  excaliflow --dir . --editorial-out "diagram.svg" --visual-type wardley --visual-data "brief.json" --canvas slide
  ```

### Nhóm 6: Hỏi Đáp Codebase Có Dẫn Chứng (Evidence-First Q&A)
- **Mục đích**: Hỏi về một biểu tượng, class, hàm hoặc kiến trúc với cam kết dẫn chứng chính xác `file:line`.
- **Lệnh thực thi**:
  ```powershell
  excaliflow ask --dir "<project_path>" --audience engineer --question "<câu hỏi>"
  # Hoặc cho người mới học code:
  excaliflow ask --dir "<project_path>" --audience learner --question "<câu hỏi>"
  ```

### Nhóm 7: Evidence Graph Cho RAG (Bản Đồ Bằng Chứng Trích Dẫn)
- **Mục đích**: Trực quan hóa đường đi bằng chứng từ câu trả lời RAG, tránh bịa đặt thông tin.
- **Lệnh thực thi**:
  ```powershell
  excaliflow knowledge import --trace "<project>\rag-trace.json" --out "<project>\evidence-graph.json"
  excaliflow knowledge atlas --graph "<project>\evidence-graph.json" --out "<project>\evidence-atlas.html"
  ```

### Nhóm 8: Atlas AI Bridge Doctor
- **Mục đích**: Chẩn đoán kết nối backend AI cục bộ cho Atlas.
- **Cổng mặc định**: Atlas Bridge `127.0.0.1:8788`; AIOS IDE bridge `127.0.0.1:8585`; Gemini Web2API `127.0.0.1:8081`.
- **Lệnh thực thi**:
  ```powershell
  excaliflow bridge init --dir "<project_path>"
  excaliflow bridge start --dir "<project_path>"
  excaliflow bridge doctor --dir "<project_path>"
  ```

### Nhóm 9: Atlas, Explain, Watch & Offline Check
- **Mục đích**: Xuất Atlas/guide tĩnh, theo dõi thay đổi source và xác minh tài nguyên offline.
- **Lệnh thực thi**:
  ```powershell
  excaliflow atlas --dir "<project_path>" --audience learner --out "codebase-atlas.html"
  excaliflow explain --dir "<project_path>" --audience engineer --out "CODEBASE_GUIDE.md"
  excaliflow --dir "<project_path>" --watch
  excaliflow --offline-check
  ```

### Nhóm 10: Cài Đặt Skill Cho AI Host
- **Mục đích**: Xem target được hỗ trợ, cài skill và xác minh đúng vị trí host.
- **Lệnh thực thi**:
  ```powershell
  excaliflow targets
  excaliflow install --host antigravity
  excaliflow doctor --host antigravity
  ```

### Nhóm 11: Kiểm Tra Cập Nhật
- **Mục đích**: Kiểm tra phiên bản mới nhất từ kho GitHub ExcaliFlow-Studio.
- **Lệnh thực thi**:
  ```powershell
  excaliflow update check
  ```
