# ExcaliFlow Studio

<p align="center">
  <strong>Bộ Công Cụ Trực Quan Hóa Kiến Trúc & Khám Phá Codebase Cục Bộ Tối Thượng</strong>
</p>

<p align="center">
  <a href="https://github.com/Nakazasen/ExcaliFlow-Studio/releases"><img src="https://img.shields.io/badge/phiên_bản-v0.1.2-blue.svg" alt="Phiên bản"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-brightgreen.svg" alt="Python 3.11+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/giấy_phép-MIT-purple.svg" alt="Giấy phép"></a>
  <a href="tests/"><img src="https://img.shields.io/badge/kiểm_thử-47%2F47%20đạt-success.svg" alt="Kiểm thử"></a>
  <a href="#tính-năng-nổi-bật"><img src="https://img.shields.io/badge/offline-100%25%20không%20phụ%20thuộc%20mạng-orange.svg" alt="Hoạt động offline"></a>
</p>

<p align="center">
  <a href="README.md"><strong>English</strong></a> • <a href="README_VI.md"><strong>Tiếng Việt</strong></a>
</p>

---

## 🌟 Giới Thiệu Chung

**ExcaliFlow Studio** là bộ công cụ tối ưu chạy **hoàn toàn cục bộ (100% Offline & Local-first)** dành cho kỹ sư phần mềm, kiến trúc sư hệ thống và người mới học code. Hệ thống quét cấu trúc mã nguồn (AST) hoặc đồ thị tri thức (Graphify) để tự động tạo ra các bản đồ web tương tác, file vẽ tay `.excalidraw`, sơ đồ SVG chuẩn thuyết trình/báo cáo, cùng hệ thống hỏi đáp mã nguồn có dẫn chứng chính xác `file:line`.

---

## 🚀 Tính Năng Nổi Bật

- **🔒 100% Cục Bộ & Bảo Mật Tuyệt Đối**: Không thu thập dữ liệu, không gửi code lên đám mây, hoạt động hoàn hảo trong môi trường mạng nội bộ (air-gapped).
- **🗺️ Codebase Atlas (Khám Phá & Học Code)**: Trả lời ứng dụng làm gì, tạo lộ trình đọc code 1→2→3 và sơ đồ quan hệ import trực quan bằng SVG native.
- **🎨 Đa Dạng Định Dạng Trực Quan**:
  - Trình xem HTML offline kèm tính năng Pan/Zoom mượt mà.
  - Tệp `.excalidraw` tương thích đầy đủ để chỉnh sửa tay.
  - Sơ đồ vector SVG độ phân giải cao dùng cho Slide thuyết trình 16:9, Sách trắng và Tài liệu kỹ thuật.
- **🧠 Bộ Xử Lý Văn Bản Thông Minh Đa Dòng (Typography Engine)**: Tự động ngắt dòng theo từ ngữ (`<tspan>`), tự điều chỉnh khoảng cách trục Y, nhúng tooltip `<title>` bảo toàn 100% nội dung gốc khi rê chuột, tự động đảo hướng neo tránh tràn mép canvas.
- **🔍 Hỏi Đáp Mã Nguồn Kèm Dẫn Chứng**: Trả lời chính xác về class, hàm, quan hệ phụ thuộc với số dòng và file cụ thể.
- **🔗 Evidence Graph Cho RAG**: Chuyển đổi dấu vết truy xuất (`rag-trace.json`) thành bản đồ xác minh nguồn trích dẫn, chống bịa đặt thông tin.
- **🤖 Tích Hợp Skill Cho Mọi AI Host**: Cài đặt 1 lệnh cho Claude Code, Cursor, Google Antigravity, GitHub Copilot, OpenAI Codex, Gemini CLI, OpenCode, Kiro.

---

## 📦 Hướng Dẫn Cài Đặt

### Cách 1: Qua `uv` (Khuyên dùng)

```powershell
# Cài đặt công cụ CLI trực tiếp từ thư mục mã nguồn
uv tool install --editable "D:\Sandbox\ExcaliFlow Studio"

# Kiểm tra runtime offline
excaliflow --offline-check
```

### Cách 2: Qua `pip`

```powershell
git clone https://github.com/Nakazasen/ExcaliFlow-Studio.git
cd ExcaliFlow-Studio
pip install -e .
```

### Cách 3: Bộ Cài Đặt 1-Click Cho Windows (Không Cần Cài Python Trước)

Tải tệp `ExcaliFlow-Setup-windows.zip` từ [Bản Phát Hành GitHub Mới Nhất](https://github.com/Nakazasen/ExcaliFlow-Studio/releases/latest), giải nén và nhấp đúp vào `ExcaliFlow-Setup.cmd`.

---

## 🛠️ Danh Mục Tính Năng & Hướng Dẫn Lệnh CLI

| Nhóm Tính Năng | Mô Tả & Sản Phẩm Đầu Ra | Lệnh CLI Thực Thi |
| :--- | :--- | :--- |
| **1. Sơ Đồ Kiến Trúc & Excalidraw** | Quét codebase $\to$ Xuất HTML Panzoom offline + file `.excalidraw` chỉnh sửa tay | `excaliflow --dir . --with-excalidraw --open` |
| **2. Codebase Atlas (Học Code)** | Giao diện web tương tác giải thích ứng dụng, lộ trình đọc code & vai trò module | `excaliflow open --dir .` |
| **3. Sơ Đồ Xuất Bản Editorial** | Xuất SVG/HTML: Wardley Map, Sankey Flow, User Journey, Slide 16:9, Báo cáo KPI/Risk | `excaliflow --editorial-out out.svg --visual-type wardley --visual-data brief.json --canvas slide` |
| **4. Hỏi Đáp Có Dẫn Chứng** | Trả lời câu hỏi về hàm/class/import kèm dẫn chứng chính xác `file:line` | `excaliflow ask --dir . --audience engineer --question "..."` |
| **5. Evidence Graph Cho RAG** | Chuyển đổi log RAG thành bản đồ trực quan xác minh nguồn trích dẫn | `excaliflow knowledge import` & `atlas` |
| **6. Atlas AI Bridge & Chẩn Đoán** | Quản lý cầu nối AI Sidecar (`:8788`) và kiểm tra kết nối Gemini Web2API (`:8081`) | `excaliflow bridge doctor --dir .` |
| **7. Kiểm Tra Bản Cập Nhật** | Kiểm tra phiên bản mới từ GitHub Release của ExcaliFlow-Studio | `excaliflow update check` |

---

### 1. Sơ Đồ Kiến Trúc Toàn Diện & Scene Excalidraw

Phân tích cấu trúc thư mục hoặc đồ thị tri thức `graphify-out/graph.json` thành sơ đồ tương tác:

```powershell
# Tạo giao diện HTML và tệp .excalidraw vẽ tay
excaliflow --dir "D:\MyProject" --with-excalidraw --out "D:\MyProject\architecture.html" --open

# Lắng nghe thay đổi file để tự động vẽ lại
excaliflow --dir "D:\MyProject" --watch
```

---

### 2. Codebase Atlas (Khám Phá & Học Code Cho Người Mới)

Dành cho việc tiếp cận nhanh một dự án mới mà không cần đọc thủ công hàng trăm tệp:

```powershell
# Mở Codebase Atlas trực tiếp trên trình duyệt
excaliflow open --dir "D:\MyProject"

# Tạo tệp HTML tĩnh
excaliflow atlas --dir "D:\MyProject" --audience learner --out "D:\MyProject\codebase-atlas.html"
```

- **Ứng dụng này làm gì?**: Tổng kết ngắn gọn, thực tế dựa trên điểm khởi chạy và cấu hình.
- **Lộ trình đọc code 1-2-3**: Gợi ý thứ tự tệp nên đọc đầu tiên.
- **Khối trách nhiệm module**: Phân nhóm các thành phần kèm dẫn chứng.

---

### 3. Sơ Đồ Xuất Bản Editorial (Slide 16:9, Báo Cáo, Sách Trắng)

Tạo sơ đồ vector SVG chất lượng cao, sử dụng font chữ thanh lịch Georgia/Arial:

```powershell
# Bản đồ Wardley Map (Tiến hóa công nghệ & chuỗi giá trị)
excaliflow --editorial-out "wardley.svg" --visual-type wardley --visual-data "brief.json" --canvas slide

# Biểu đồ Sankey (Dòng chảy dữ liệu & tài nguyên)
excaliflow --editorial-out "sankey.svg" --visual-type sankey --visual-data "brief.json" --canvas document

# Bản đồ trải nghiệm người dùng (User Journey Map)
excaliflow --editorial-out "journey.svg" --visual-type journey --visual-data "brief.json" --canvas slide

# Báo cáo kinh doanh (kpi, funnel, timeline, process, quadrant, matrix, risk)
excaliflow --editorial-out "kpi.svg" --visual-type kpi --visual-data "kpi-data.json" --canvas slide
```

Các loại sơ đồ hỗ trợ (`--visual-type`):
`architecture` • `wardley` • `sankey` • `journey` • `kpi` • `funnel` • `timeline` • `process` • `quadrant` • `matrix` • `risk`

---

### 4. Hỏi Đáp Codebase Có Dẫn Chứng

Đặt câu hỏi cụ thể và nhận câu trả lời có cam kết dẫn chứng `file:line`:

```powershell
# Dành cho kỹ sư (chi tiết kỹ thuật chuyên sâu):
excaliflow ask --dir "D:\MyProject" --audience engineer --question "UserService thực hiện chức năng gì?"

# Dành cho người mới học (giải thích kiến trúc mức cao, dễ hiểu):
excaliflow ask --dir "D:\MyProject" --audience learner --question "Các module kết nối với nhau như thế nào?"

# Xuất cẩm nang đọc hiểu mã nguồn dạng Markdown:
excaliflow explain --dir "D:\MyProject" --audience learner --out "D:\MyProject\HUONG_DAN_CODEBASE.md"
```

---

### 5. Evidence Graph Cho RAG (Xác Minh Trích Dẫn)

Kiểm tra tính chính xác của câu trả lời từ hệ thống RAG:

```powershell
# 1. Chuyển đổi log truy xuất RAG thành đồ thị bằng chứng chuẩn
excaliflow knowledge import --trace ".\examples\rag-trace.json" --out ".\evidence-graph.json"

# 2. Tạo giao diện web Evidence Atlas HTML độc lập
excaliflow knowledge atlas --graph ".\evidence-graph.json" --out ".\evidence-atlas.html"
```

---

### 6. Atlas AI Bridge & Chẩn Đoán Kết Nối

Kết nối backend AI cục bộ (Sidecar Antigravity `:8585` hoặc [Gemini Web2API](https://github.com/Sophomoresty/gemini-web2api) `:8081`):

```powershell
# Khởi tạo tệp manifest (.excaliflow/ide-bridge.json)
excaliflow bridge init --dir "D:\MyProject"

# Khởi chạy cầu nối cục bộ (chỉ liên kết 127.0.0.1:8788)
excaliflow bridge start --dir "D:\MyProject"

# Chẩn đoán trạng thái kết nối
excaliflow bridge doctor --dir "D:\MyProject"
```

---

### 7. Cài Đặt Skill Cho Các Nền Tảng AI Agent

Cài đặt ExcaliFlow như một kỹ năng (skill) gốc vào các trợ lý lập trình AI:

```powershell
# Xem danh sách các thư mục skill được hỗ trợ
excaliflow targets

# Cài đặt cho nền tảng cụ thể
excaliflow install --host claude       # Claude Code
excaliflow install --host antigravity   # Google Antigravity
excaliflow install --host copilot       # GitHub Copilot
excaliflow install --host codex         # OpenAI Codex
excaliflow install --host gemini        # Gemini CLI
excaliflow install --host custom --target "D:\DuongDan\Skills\excaliflow"
```

---

## 🧪 Kiểm Thử & Xác Minh Hệ Thống

Toàn bộ hệ thống được bảo đảm bằng bộ kiểm thử tự động toàn diện:

```powershell
# Chạy toàn bộ bộ test
uv run python -m unittest discover -s tests -v

# Kiểm tra tài nguyên offline (Mermaid & Panzoom)
uv run excaliflow --offline-check
```

---

## 📁 Cấu Trúc Thư Mục Dự Án

```text
ExcaliFlow-Studio/
├── src/excaliflow/         # Gói mã nguồn chính, bộ điều phối CLI & động cơ Atlas
│   ├── cli.py              # Điểm khởi chạy CLI
│   ├── atlas.py            # Trình tạo Codebase Atlas tương tác
│   ├── bridge_server.py    # Máy chủ AI Bridge cục bộ
│   ├── explorer.py         # Bộ quét AST & phân tích hỏi đáp có bằng chứng
│   ├── knowledge.py        # Bộ xử lý đồ thị bằng chứng RAG
│   └── installer.py        # Bộ cài đặt skill cho các AI Host
├── scripts/
│   └── generate_diagram.py # Bộ sinh sơ đồ kiến trúc & SVG Editorial
├── assets/vendor/          # Thư viện JavaScript offline (Mermaid, Panzoom)
├── docs/                   # Tài liệu hướng dẫn & thiết lập AI Bridge
├── examples/               # Mẫu brief sơ đồ & tệp mẫu RAG trace
├── tests/                  # Bộ kiểm thử tự động (47 tests)
├── SKILL.md                # Giao thức skill điều khiển cho Agent (v3.1)
├── pyproject.toml          # Cấu hình gói dự án
└── VERSION                 # Tệp định danh phiên bản
```

---

## 📄 Giấy Phép (License)

Dự án được phân phối theo [Giấy phép MIT](LICENSE).
Các thư viện bên thứ ba đi kèm được ghi nhận tại [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
