# backend/

Phần "CI/CD" của dự án — dữ liệu (`data/`), design gốc (`templates/`), và builder (`scripts/build.py`) biến dữ liệu thành site tĩnh trong `../html/`.

| Thư mục | Ai ghi | Vai trò |
|---|---|---|
| `data/` | GAS CMS (xem `data/README.md`) | Nguồn dữ liệu: danh mục, bài viết |
| `templates/index.html`, `category.html`, `post.html` | **sửa tay** | Design gốc (placeholder `{{...}}`) — đây là chỗ sửa giao diện |
| `scripts/build.py` | sửa tay | Builder, Python stdlib, chạy được cả local lẫn CI |

Workflow CI (`../.github/workflows/build.yml`) **nằm ở gốc repo**, không nằm trong `backend/` — đây là yêu cầu kỹ thuật của GitHub Actions (chỉ nhận `.github/workflows/` ở repo root), dù về mặt logic nó thuộc "CI/CD" của `backend/`.

## Chạy build local

```bash
python3 backend/scripts/build.py
```

Ghi đè `../html/index.html`, `../html/<category-slug>/index.html`, `../html/<slug>/index.html`, `../html/sitemap.xml`. Không đụng `../html/css`, `../html/fonts`, `../html/images` (copy tĩnh 1 lần, xem README gốc).

## Quyết định thiết kế riêng của dự án này

- **Không có field `order` cho danh mục** — thứ tự hiển thị (menu + trang chủ) hoàn toàn theo `created_at` tăng dần (tạo trước → hiện trước), đúng yêu cầu ban đầu. Nếu sau này cần sắp tay, thêm field `order` theo đúng pattern đã dùng cho `Posts` ở dự án mvngroup (xem skill `free-cms-static-site-pipeline`).
- **Không có pagination cho trang danh mục** — liệt kê toàn bộ bài trong danh mục trên 1 trang. Khi 1 danh mục có hàng trăm bài, cân nhắc thêm phân trang (không nằm trong yêu cầu ban đầu).
- **Slug dùng chung 1 namespace** giữa category và post (`/<slug>/` phẳng ở gốc site) — GAS phải kiểm tra trùng slug CHÉO giữa 2 sheet `Categories` và `Posts`, không chỉ trong cùng 1 sheet.
- **Ảnh cover được crop 3:2 từ tâm ở phía CLIENT (canvas)** trước khi upload, không phải ở build.py hay ở GAS — GAS không có API xử lý ảnh (crop), nên phải làm ở trình duyệt lúc chọn ảnh (xem `gas/js.html`, hàm `cropCoverTo3x2`).
