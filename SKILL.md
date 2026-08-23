---
name: excaliflow
description: "Trung tâm điều khiển trực quan hóa kiến trúc ExcaliFlow Studio: Phân tích codebase/Graphify thành sơ đồ Excalidraw, Codebase Atlas, sơ đồ Editorial (Wardley, Sankey, Journey, Architecture), và Evidence Graph cho RAG."
---

# Excali-Flow Skill: Visual Architecture & Diagramming Protocol (v3.1)

> **MỤC TIÊU CỐT LÕI**: Khi người dùng gõ `/excaliflow` (hoặc gọi skill này mà chưa chỉ định cụ thể tham số phức tạp), Agent **BẮT BUỘC** hiển thị ngay **BẢNG TÍNH NĂNG ĐIỀU KHIỂN (ExcaliFlow Feature Dashboard)** để người dùng chọn nhanh tính năng mong muốn (bằng số hoặc mô tả) thay vì phải tự nhớ lệnh.

---

## 📋 BẢNG TÍNH NĂNG ĐIỀU KHIỂN (ExcaliFlow Feature Dashboard)

Khi người dùng kích hoạt `/excaliflow`, hãy chào người dùng và hiển thị ngay bảng tính năng sau:

| STT | Nhóm Tính Năng | Mô Tả & Sản Phẩm Đầu Ra | Hành Động CLI / Lệnh Mẫu |
| :---: | :--- | :--- | :--- |
| **1** | 🏢 **Sơ Đồ Kiến Trúc & Excalidraw** | Quét Graphify/AST $\to$ Xuất HTML Panzoom offline + file `.excalidraw` chỉnh sửa tay | `excaliflow --dir . --with-excalidraw --open` |
| **2** | 🗺️ **Codebase Atlas (Học Codebase)** | Giao diện tương tác đọc hiểu codebase, giải thích ứng dụng, đọc sơ đồ SVG native | `excaliflow open --dir .` |
| **3** | 📊 **Sơ Đồ Editorial (Slide 16:9 / Doc)** | Xuất SVG/HTML: Wardley Map, Sankey Flow, User Journey, Architecture Slide | `excaliflow --editorial-out <out> --visual-type <type>` |
| **4** | 🔍 **Hỏi Đáp Codebase Có Dẫn Chứng** | Phân tích AST và trả lời câu hỏi về hàm/class/import kèm file:line dẫn chứng | `excaliflow ask --dir . --audience engineer --question "..."` |
| **5** | 🔗 **Evidence Graph Cho RAG & Điều Tra** | Chuyển đổi `rag-trace.json` $\to$ Bản đồ tương tác xác minh nguồn trích dẫn | `excaliflow knowledge import` & `atlas` |
| **6** | 🩺 **Atlas AI Bridge Doctor** | Kiểm tra trạng thái kết nối Sidecar Daemon (`:8585`) và Gemini Web2API (`:8081`) | `excaliflow bridge doctor --dir .` |
| **7** | 🔄 **Kiểm Tra Bản Cập Nhật** | Kiểm tra phiên bản mới từ GitHub Release của ExcaliFlow-Studio | `excaliflow update check` |

---

## 🛠️ Hướng Dẫn Thực Thi Chi Tiết Từng Nhóm

### Nhóm 1: Sơ Đồ Kiến Trúc Toàn Diện & Scene Excalidraw (Tích Hợp Graphify)
- **Mục đích**: Phân tích đồ thị tri thức `graphify-out/graph.json` thành sơ đồ tương tác & bản vẽ Excalidraw.
- **Quy trình thực thi bắt buộc**:
  1. *Đồng bộ tri thức*: Nếu có `graphify`, chạy cập nhật/trích xuất đồ thị:
     ```powershell
     graphify extract "<project_path>" --code-only --out "<project_path>"
     ```
  2. *Vẽ sơ đồ Excalidraw*: Tự động đọc đồ thị và tạo viewer HTML + file `.excalidraw`:
     ```powershell
     excaliflow --dir "<project_path>" --with-excalidraw --out "<project_path>\architecture_viewer.html" --open
     ```

### Nhóm 2: Codebase Atlas (Khám Phá & Học Code Cho Người Mới)
- **Mục đích**: Tạo trang web giải thích ứng dụng làm gì, 1-2-3 reading path, trách nhiệm từng module.
- **Lệnh thực thi**:
  ```powershell
  excaliflow open --dir "<project_path>"
  ```

### Nhóm 3: Sơ Đồ Xuất Bản Editorial (Slide 16:9, Báo Cáo, Sách Trắng)
- **Mục đích**: Vẽ các sơ đồ trừu tượng chất lượng cao, không phụ thuộc font mạng.
- **Các loại sơ đồ hỗ trợ (`--visual-type`)**:
  1. `architecture`: Sơ đồ kiến trúc tối giản cho slide thuyết trình.
  2. `wardley`: Bản đồ tiến hóa công nghệ (Genesis $\to$ Custom $\to$ Product $\to$ Commodity) kèm chuỗi giá trị.
  3. `sankey`: Biểu đồ dòng chảy dữ liệu / luân chuyển giá trị giữa các node.
  4. `journey`: Bản đồ trải nghiệm người dùng / các giai đoạn phát triển theo thời gian.
- **Lệnh thực thi**:
  ```powershell
  excaliflow --dir . --editorial-out "diagram.svg" --visual-type wardley --visual-data "brief.json" --canvas slide
  ```

### Nhóm 4: Hỏi Đáp Codebase Có Dẫn Chứng (Evidence-First Q&A)
- **Mục đích**: Hỏi về một biểu tượng, class, hàm hoặc kiến trúc với cam kết dẫn chứng chính xác `file:line`.
- **Lệnh thực thi**:
  ```powershell
  excaliflow ask --dir "<project_path>" --audience engineer --question "<câu hỏi>"
  # Hoặc cho người mới học code:
  excaliflow ask --dir "<project_path>" --audience learner --question "<câu hỏi>"
  ```

### Nhóm 5: Evidence Graph Cho RAG (Bản Đồ Bằng Chứng Trích Dẫn)
- **Mục đích**: Trực quan hóa đường đi bằng chứng từ câu trả lời RAG, tránh bịa đặt thông tin.
- **Lệnh thực thi**:
  ```powershell
  excaliflow knowledge import --trace "<project>\rag-trace.json" --out "<project>\evidence-graph.json"
  excaliflow knowledge atlas --graph "<project>\evidence-graph.json" --out "<project>\evidence-atlas.html"
  ```

### Nhóm 6: Atlas AI Bridge Doctor
- **Mục đích**: Chẩn đoán kết nối backend AI cục bộ cho Atlas.
- **Lệnh thực thi**:
  ```powershell
  excaliflow bridge doctor --dir "<project_path>"
  ```

### Nhóm 7: Kiểm Tra Cập Nhật
- **Mục đích**: Kiểm tra phiên bản mới nhất từ kho GitHub ExcaliFlow-Studio.
- **Lệnh thực thi**:
  ```powershell
  excaliflow update check
  ```
