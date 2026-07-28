# data/

Nguồn dữ liệu — do GAS CMS ghi (qua GitHub Contents API), **không sửa tay** trừ `site.json`.

| File | Ai ghi | Nội dung |
|---|---|---|
| `site.json` | người, tay | `site_name` / `site_url` / `tagline` — đổi khi có domain thật |
| `categories.json` | GAS | Toàn bộ danh mục: `{id, name, slug, created_at}`. Thứ tự hiển thị (trang chủ + menu) = sắp theo `created_at` tăng dần, KHÔNG lưu field `order` riêng — tạo trước lên trước. |
| `posts.json` | GAS | Index metadata mọi bài (không có `content`, để payload nhẹ). |
| `posts/<slug>/detail.json` | GAS | 1 bài đầy đủ (metadata + `content` HTML). |

`build.py` đọc các file này + `templates/*.html` để build ra `../html/`. Xoá category/post trong CMS sẽ tự xoá luôn thư mục tương ứng trong `html/` (GAS gọi thẳng GitHub API xoá dir) — `build.py` không tự xoá gì, chỉ build/ghi đè các trang đang tồn tại trong data.
