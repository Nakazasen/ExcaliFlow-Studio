# ExcaliFlow Studio

<p align="center">
  <strong>Bộ Công Cụ Trực Quan Hóa Kiến Trúc & Khám Phá Codebase Cục Bộ Tối Thượng</strong>
</p>

<p align="center">
  <a href="https://github.com/Nakazasen/ExcaliFlow-Studio/releases"><img src="https://img.shields.io/badge/phiên_bản-v0.1.4-blue.svg" alt="Phiên bản"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-brightgreen.svg" alt="Python 3.11+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/giấy_phép-MIT-purple.svg" alt="Giấy phép"></a>
  <a href="tests/"><img src="https://img.shields.io/badge/kiểm_thử-64%2F64%20đạt-success.svg" alt="Kiểm thử"></a>
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
- **⚡ Truy Vết Lan Truyền Tương Tác (Reach Tracing)**: Click vào bất kỳ node nào để cô lập ngay luồng gọi đến (Upstream - Xanh ngọc) và luồng phụ thuộc (Downstream - Xanh lá), làm mờ các thành phần ngoài ngữ cảnh.
- **✨ Hiệu Ứng Luồng Chuyển Động (Animated Signal Flow)**: Bật/tắt dòng xung chuyển động dọc theo các cạnh kết nối để mô phỏng dòng dữ liệu thời gian thực.
- **🔍 So Sánh Kiến Trúc (Architecture Diff Engine)**: So sánh độ lệch kiến trúc giữa 2 snapshot hoặc git commit (Added, Removed, Modified) trước khi merge PR (`--diff`).
- **🎴 Thẻ Ảnh Bìa 1200×630 (README Share Card)**: Tự động sinh thẻ ảnh vector chuẩn 1200×630 đính kèm đầu `README.md` và chia sẻ mạng xã hội (`--share-card`).
- **🗺️ Codebase Atlas (Khám Phá & Học Code)**: Trả lời ứng dụng làm gì, tạo lộ trình đọc code 1→2→3 và sơ đồ quan hệ import trực quan bằng SVG native.
- **🎨 Đa Dạng Định Dạng Trực Quan**: Trình xem HTML offline kèm tính năng Pan/Zoom mượt mà, tệp `.excalidraw` tương thích đầy đủ để chỉnh sửa tay, và sơ đồ vector SVG độ phân giải cao dùng cho Slide thuyết trình 16:9, Sách trắng và Tài liệu kỹ thuật.
- **🧠 Bộ Xử Lý Văn Bản Thông Minh Đa Dòng (Typography Engine)**: Tự động ngắt dòng theo từ ngữ (`<tspan>`), tự điều chỉnh khoảng cách trục Y, nhúng tooltip `<title>` bảo toàn 100% nội dung gốc khi rê chuột, tự động đảo hướng neo tránh tràn mép canvas.
- **🔍 Hỏi Đáp Mã Nguồn Kèm Dẫn Chứng**: Trả lời chính xác về class, hàm, quan hệ phụ thuộc với số dòng và file cụ thể.
- **🔗 Evidence Graph Cho RAG**: Chuyển đổi dấu vết truy xuất (`rag-trace.json`) thành bản đồ xác minh nguồn trích dẫn, chống bịa đặt thông tin.
- **🤖 Tích Hợp Skill Cho Mọi AI Host**: Cài đặt 1 lệnh cho Claude Code, Cursor, Google Antigravity, GitHub Copilot, OpenAI Codex, Gemini CLI, OpenCode, Kiro.

---

## ⚡ Bắt Đầu Nhanh Trong 5 Giây (Dành Cho Người Mới — Không Cần Cài Đặt Phức Tạp!)

Bạn **không cần bất kỳ công cụ phụ trợ hay cấu hình phức tạp nào** để vẽ sơ đồ dự án. ExcaliFlow hoạt động hoàn toàn độc lập ngay sau khi cài:

### 1. Cài đặt ExcaliFlow
```bash
pip install -e .
# hoặc qua uv:
uv tool install --editable .
```

### 2. Chạy ngay tại thư mục dự án của bạn
```bash
# Di chuyển đến thư mục code cần vẽ
cd /duong/dan/toi/du/an

# Tạo và tự động mở sơ đồ ngay lập tức
excaliflow --open --with-excalidraw
```
🎉 **Xong ngay!** Trình duyệt web sẽ tự động bật lên với giao diện phóng to/thu nhỏ (Panzoom) toàn cảnh kiến trúc dự án và file `.excalidraw` sẵn sàng để vẽ tay hoặc thuyết trình!

---

## 💡 Chế Độ Độc Lập vs. Siêu Cấp: Tôi Có Bắt Buộc Cần `/graphify` Không?

| Chế Độ | Cơ Chế Hoạt Động | Khi Nào Nên Dùng |
| :--- | :--- | :--- |
| 🚀 **Chế Độ Độc Lập (Standalone)** *(Mặc định — Không cần cài thêm gì)* | ExcaliFlow tự động quét cấu trúc cây thư mục (AST), đọc các quan hệ import và tạo sơ đồ kiến trúc ngay tức thì. | Bạn muốn có ngay một sơ đồ kiến trúc đẹp, trực quan cho dự án chỉ trong 5 giây mà không cần cài thêm công cụ ngoài. |
| ⚡ **Chế Độ Siêu Cấp (Supercharged with `/graphify`)** *(Tùy chọn nâng cao)* | **Graphify là gì?** Là công cụ AI mã nguồn mở giúp biến toàn bộ codebase thành Đồ thị tri thức (Knowledge Graph), tự phát hiện các file trung tâm cốt lõi (God-nodes) và gom cụm đa chiều. Nếu máy bạn đã có `graphify`, ExcaliFlow sẽ **tự động kích hoạt** để vẽ đồ thị sâu hơn gấp 10 lần mà bạn không cần gõ thêm lệnh nào! | Dự án lớn, cấu trúc phức tạp và bạn muốn phân tích sâu cấu trúc cộng đồng mã nguồn bằng đồ thị tri thức. |

ExcaliFlow chấp nhận Graphify `>=0.9.48,<0.10`: vẫn nhận các bản vá tương thích nhưng không âm thầm nhận một bản minor mới chưa được kiểm chứng. `uv.lock` cố ý ghi đúng một phiên bản để môi trường phát triển và CI có thể tái tạo. Khi chạy, CLI ngoài khoảng tương thích sẽ fallback sang AST; chế độ `--strict` sẽ dừng an toàn và đưa ra lệnh cài đặt cụ thể.

```text
┌─────────────────────────┐       ┌──────────────────────────────────────┐       ┌──────────────────────────────┐
│  Mã Nguồn Codebase      │ ────> │  ExcaliFlow Độc Lập (AST / Code)     │ ────> │  Trình Xem HTML Tương Tác    │
│  (Python, JS, TS, v.v.) │   │   └──────────────────────────────────────┘   │   │  (Reach Tracing + Luồng Xung)│
│                         │   │   ┌──────────────────────────────────────┐   │   │  + Bản Vẽ Tay .excalidraw    │
│                         │   └──>│  Tùy chọn: /graphify Đồ Thị Tri Thức │───┘   │  + Thẻ Ảnh Bìa 1200x630 SVG  │
└─────────────────────────┘       └──────────────────────────────────────┘       └──────────────────────────────┘
```

---

## 🤖 Cách Dùng Nhanh Cho AI Agent: Bảng Điều Khiển Skill `/excaliflow`

Nếu bạn sử dụng các IDE AI / Coding Agent (**Antigravity, Codex, Cursor, Claude Code, GitHub Copilot, Gemini CLI**):

1. Chỉ cần gõ `/excaliflow` trong khung chat AI.
2. AI Agent sẽ **tự động hiển thị Bảng Menu Điều Khiển 1-Chạm (Dashboard v3.7)**:
   - `1` 🏢 **Sơ Đồ Kiến Trúc & Excalidraw (Reach Tracing + Luồng Chuyển Động)**
   - `2` 🔍 **So Sánh Độ Lệch Kiến Trúc (`--diff`)**
   - `3` 🎴 **Thẻ Ảnh Bìa 1200×630 (`--share-card`)**
   - `4` 🗺️ **Codebase Atlas (Khám Phá & Học Code)**
   - `5` 📊 **Sơ Đồ Xuất Bản Editorial (Wardley, Sankey, Journey, Slide)**
   - `6` 🔍 **Hỏi Đáp Codebase Có Dẫn Chứng**
   - `7` 🔗 **Evidence Graph Cho RAG**
   - `8` 🩺 **Vòng Đời Atlas AI Bridge**
   - `9` 📖 **Atlas, Explain, Watch & Offline Check**
   - `10` 🧩 **Cài Đặt/Chẩn Đoán Skill Cho AI Host**
   - `11` 🔄 **Kiểm Tra Bản Cập Nhật**
3. Bạn chỉ cần gõ số (vd: `1` hoặc `2`)—**không cần nhớ bất kỳ cờ lệnh CLI phức tạp nào!**

---

## 🛠️ Danh Mục Tính Năng & Hướng Dẫn Lệnh CLI

| Nhóm Tính Năng | Mô Tả & Sản Phẩm Đầu Ra | Lệnh CLI Thực Thi |
| :--- | :--- | :--- |
| **1. Sơ Đồ Kiến Trúc & Excalidraw** | Quét codebase $\to$ HTML Panzoom (Reach Tracing + Animated Flow) + `.excalidraw` | `excaliflow --dir . --with-excalidraw --open` |
| **2. So Sánh Kiến Trúc (Diff)** | So sánh độ lệch kiến trúc với snapshot cũ hoặc git commit | `excaliflow --diff HEAD~1 --open` |
| **3. Thẻ Ảnh Bìa 1200×630** | Xuất thẻ ảnh vector 1200×630 dùng cho README và chia sẻ | `excaliflow --share-card "README_CARD.svg" --open` |
| **4. Codebase Atlas (Học Code)** | Giao diện web tương tác giải thích ứng dụng, lộ trình đọc code & vai trò module | `excaliflow open --dir .` |
| **5. Sơ Đồ Xuất Bản Editorial** | Xuất SVG/HTML: Wardley Map, Sankey Flow, User Journey, Slide 16:9, Báo cáo KPI/Risk | `excaliflow --editorial-out out.svg --visual-type wardley --visual-data brief.json --canvas slide` |
| **6. Tra Cứu Source Có Dẫn Chứng** | Tra cứu hàm/class/file/import kèm `file:line`; câu trả lời semantic cần Atlas Bridge khỏe | `excaliflow ask --dir . --audience engineer --question "..."` |
| **7. Evidence Graph Cho RAG** | Chuyển đổi log RAG thành bản đồ trực quan xác minh nguồn trích dẫn | `excaliflow knowledge import` & `atlas` |
| **8. Điều Khiển & Chẩn Đoán Atlas Bridge** | Cấu hình/chạy Atlas Bridge (`:8788`) và chẩn đoán riêng Atlas, AIOS IDE bridge (`:8585`), Gemini Web2API (`:8081`); không tự khởi động dịch vụ ngoài | `excaliflow bridge init/start/doctor --dir .` |
| **9. Atlas, Explain & Theo Dõi** | Xuất Atlas/guide, theo dõi source và kiểm tra tài nguyên offline | `excaliflow atlas`, `explain`, `--watch`, `--offline-check` |
| **10. Cài Skill Cho AI Host** | Liệt kê target, cài đặt và chẩn đoán skill portable cho các AI host | `excaliflow targets/install/doctor` |
| **11. Kiểm Tra Bản Cập Nhật** | Kiểm tra phiên bản mới từ GitHub Release của ExcaliFlow-Studio | `excaliflow update check` |

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
# Khởi tạo manifest riêng của ExcaliFlow (.excaliflow/atlas-bridge.json)
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
├── docs/                   # Hướng dẫn thiết lập & Sổ tay bảo trì (maintenance-and-architecture.md)
├── examples/               # Mẫu brief sơ đồ & tệp mẫu RAG trace
├── tests/                  # Bộ kiểm thử tự động (65 tests)
├── SKILL.md                # Giao thức skill điều khiển cho Agent (v3.7)
├── pyproject.toml          # Cấu hình gói dự án
└── VERSION                 # Tệp định danh phiên bản (0.1.4)
```

---

## 📄 Giấy Phép (License)

Dự án được phân phối theo [Giấy phép MIT](LICENSE).
Các thư viện bên thứ ba đi kèm được ghi nhận tại [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
