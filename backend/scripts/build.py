#!/usr/bin/env python3
"""
Build static HTML from data/ (run by GitHub Actions; stdlib only, no pip install needed).

Input:
  data/site.json                   # site_name / site_url / tagline (hand-edited config)
  data/categories.json             # danh muc, GAS ghi (index: id, name, slug, created_at)
  data/posts.json                  # bai viet, GAS ghi (index metadata, khong co content)
  data/posts/<slug>/detail.json    # noi dung day du 1 bai (content HTML + metadata)
  templates/index.html, category.html, post.html
  html/<slug>/images/*             # anh da duoc GAS day thang vao day (cover + anh trong bai)

Output:
  html/index.html                  # trang chu: 1 section/danh muc, theo dung thu tu tao truoc -> sau
  html/<category-slug>/index.html  # trang danh muc: toan bo bai trong danh muc, moi nhat truoc
  html/<post-slug>/index.html      # trang bai viet
  html/sitemap.xml                 # trang chu + moi danh muc + moi bai viet

Chay local de thu: python3 scripts/build.py
"""
import html as htmllib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent  # counrtrytales/ — html/ song song voi backend/, khong nam trong no
HTML = ROOT / "html"
DATA = BACKEND / "data"
TEMPLATES = BACKEND / "templates"

HOMEPAGE_POSTS_PER_CATEGORY = 8
PLACEHOLDER_COVER = "/images/thumbnail-placeholder.svg"


def esc(s):
    # unescape (lap toi khi on dinh) truoc khi escape lai, tranh double-encode neu noi dung
    # goc lo chua entity dang chu (vd dan tu Word/Facebook).
    s = s or ""
    for _ in range(5):
        unescaped = htmllib.unescape(s)
        if unescaped == s:
            break
        s = unescaped
    return htmllib.escape(s, quote=True)


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def parse_iso(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return datetime(2021, 1, 1, tzinfo=timezone.utc)


def date_display(iso):
    d = parse_iso(iso)
    return "%02d/%02d/%d" % (d.day, d.month, d.year)


def truncate(s, n=160):
    s = (s or "").strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def cover_of(post):
    return ("/" + post["cover"]) if post.get("cover") else PLACEHOLDER_COVER


def site_config():
    cfg = load_json(DATA / "site.json", {})
    return {
        "site_name": cfg.get("site_name") or "CountryTales",
        "site_url": (cfg.get("site_url") or "https://countrytales.vn").rstrip("/"),
        "tagline": cfg.get("tagline") or "Tin tức mới nhất mỗi ngày",
    }


# ---------- nav (header/footer shared across every page) ----------

NAV_PC_MAX = 8

TOGGLE_SCRIPT = """    <script>
      document.querySelector('.more').addEventListener('click', function () {
        var el = document.querySelector('.category-popup');
        var isActive = el.classList.contains('active');
        el.classList.toggle('active', !isActive);
        el.style.visibility = isActive ? 'hidden' : 'visible';
        el.style.opacity = isActive ? '0' : '1';
        el.style.display = isActive ? 'none' : 'block';
      });
      document.querySelectorAll('.more-cats > button').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var li = btn.closest('li');
          var willOpen = !li.classList.contains('active');
          document.querySelectorAll('.more-cats.active').forEach(function (el) { el.classList.remove('active'); });
          if (willOpen) li.classList.add('active');
        });
      });
      document.addEventListener('click', function (e) {
        if (!e.target.closest('.more-cats')) {
          document.querySelectorAll('.more-cats.active').forEach(function (el) { el.classList.remove('active'); });
        }
      });
    </script>"""


def render_header(categories, site_name):
    """categories da o dung thu tu tao truoc -> sau (categories.json)."""
    pc_cats = categories[:NAV_PC_MAX]
    overflow_cats = categories[NAV_PC_MAX:]

    pc_items = "\n".join(
        '          <li class="parent"><a href="/%s/" title="%s">%s</a></li>' % (c["slug"], esc(c["name"]), esc(c["name"]))
        for c in pc_cats
    )
    if overflow_cats:
        panel_links = "\n".join(
            '              <a href="/%s/">%s</a>' % (c["slug"], esc(c["name"])) for c in overflow_cats
        )
        pc_items += (
            "\n          <li class=\"more-cats\">"
            "\n            <button type=\"button\">Danh mục khác <span class=\"caret\"></span></button>"
            "\n            <div class=\"more-cats__panel\">\n" + panel_links + "\n            </div>"
            "\n          </li>"
        )
    pc_items += (
        "\n          <li class=\"more\">"
        "\n            <span class=\"dot dot1\"></span><span class=\"dot dot2\"></span><span class=\"dot dot3\"></span>"
        "\n          </li>"
    )

    mobile_items = "\n".join(
        '              <li class="parent"><a href="/%s/" title="%s">%s</a></li>' % (c["slug"], esc(c["name"]), esc(c["name"]))
        for c in categories
    )

    return """<header id="zing-header" class="scrollfixed">
    <div class="page-wrapper">
      <h1 class="logo"><a href="/" title="%s">%s</a></h1>
      <nav class="category-menu pc">
        <ul>
%s
        </ul>
      </nav>
    </div>
    <div class="category-popup">
      <nav class="category-menu mobile">
        <div class="page-wrapper">
          <ul class="normal-category">
%s
          </ul>
        </div>
      </nav>
    </div>
  </header>
%s""" % (esc(site_name), esc(site_name), pc_items, mobile_items, TOGGLE_SCRIPT)


def render_footer(site_name, tagline):
    return """<footer id="footer">
    <div class="page-wrapper footer-wrapper">
      <div class="left-side-info">
        <div class="web-info">
          <div class="logo">%s</div>
          <p style="line-height: 1.7; font-size: 12px">%s</p>
        </div>
      </div>
      <div class="copyright-info">
        <p style="line-height: 1.7; font-size: 12px">© %s</p>
      </div>
    </div>
  </footer>""" % (esc(site_name), esc(tagline), esc(site_name))


# ---------- card / section renderers ----------

def render_card(post):
    desc = ""
    if post.get("description"):
        desc = '\n            <p class="article-summary">%s</p>' % esc(truncate(post["description"]))
    return """        <article class="article-item type-text">
            <p class="article-thumbnail">
                <a href="/%s/">
                    <img src="%s" alt="%s" loading="lazy">
                </a>
            </p>
            <header>
                <p class="article-title">
                    <a href="/%s/">%s</a>
                </p>%s
            </header>
        </article>""" % (post["slug"], cover_of(post), esc(post["title"]), post["slug"], esc(post["title"]), desc)


def render_category_section(cat, posts_in_cat):
    shown = posts_in_cat[:HOMEPAGE_POSTS_PER_CATEGORY]
    cat_url = "/%s/" % cat["slug"]
    more_link = ""
    if len(posts_in_cat) > len(shown):
        more_link = '\n                <a class="section-more" href="%s">Xem thêm →</a>' % cat_url
    if shown:
        grid = "\n".join(render_card(p) for p in shown)
    else:
        grid = '            <p class="empty-note">Chưa có bài viết trong danh mục này.</p>'
    return """        <section class="section category-section">
            <header class="section-title">
                <h2><a href="%s">%s</a></h2>%s
            </header>
            <div class="section-content">
                <div class="article-grid">
%s
                </div>
            </div>
        </section>""" % (cat_url, esc(cat["name"]), more_link, grid)


# ---------- content transform ----------

def transform_content(content, slug):
    content = content or ""
    # src tuong doi "<slug>/images/.." -> tuyet doi "/<slug>/images/.."
    content = re.sub(r'src="%s/' % re.escape(slug), 'src="/%s/' % slug, content)
    content = re.sub(r"src='%s/" % re.escape(slug), "src='/%s/" % slug, content)
    content = re.sub(r"<img (?!loading)", '<img loading="lazy" ', content)
    return "\n".join("                " + line if line.strip() else line for line in content.splitlines())


def strip_html(s):
    return re.sub(r"<[^>]*>", " ", s or "").replace("\xa0", " ")


# ---------- builders ----------

def build_post_page(detail, cat, cfg, tpl):
    slug = detail["slug"]
    url = "%s/%s/" % (cfg["site_url"], slug)
    cover_url = cfg["site_url"] + cover_of(detail)
    description = truncate(detail.get("description") or strip_html(detail.get("content", "")), 220)
    published_iso = detail.get("created_at") or ""

    json_ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "mainEntityOfPage": {"@type": "WebPage", "@id": url},
            "headline": detail["title"],
            "description": description,
            "image": [cover_url],
            "datePublished": published_iso,
            "dateModified": detail.get("updated_at") or published_iso,
            "author": {"@type": "Organization", "name": cfg["site_name"]},
            "publisher": {"@type": "Organization", "name": cfg["site_name"]},
        },
        ensure_ascii=False,
        indent=2,
    )

    page = (
        tpl.replace("{{TITLE}}", esc(detail["title"]))
        .replace("{{DESCRIPTION}}", esc(description))
        .replace("{{URL}}", url)
        .replace("{{SITE_NAME}}", esc(cfg["site_name"]))
        .replace("{{COVER_URL}}", cover_url)
        .replace("{{PUBLISHED_ISO}}", esc(published_iso))
        .replace("{{JSON_LD}}", json_ld)
        .replace("{{CATEGORY_URL}}", "/%s/" % cat["slug"])
        .replace("{{CATEGORY_NAME}}", esc(cat["name"]))
        .replace("{{DATE_DISPLAY}}", date_display(published_iso))
        .replace("{{CONTENT}}", transform_content(detail.get("content", ""), slug))
        .replace("{{HEADER}}", render_header(ALL_CATEGORIES, cfg["site_name"]))
        .replace("{{FOOTER}}", render_footer(cfg["site_name"], cfg["tagline"]))
    )
    out = HTML / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print("built", out.relative_to(ROOT))


def build_category_page(cat, posts_in_cat, cfg, tpl):
    slug = cat["slug"]
    url = "%s/%s/" % (cfg["site_url"], slug)
    title = "%s – %s" % (cat["name"], cfg["site_name"])
    description = "Toàn bộ bài viết thuộc danh mục %s trên %s." % (cat["name"], cfg["site_name"])

    if posts_in_cat:
        grid = "\n".join(render_card(p) for p in posts_in_cat)
    else:
        grid = '                <p class="empty-note">Chưa có bài viết trong danh mục này.</p>'

    page = (
        tpl.replace("{{TITLE}}", esc(title))
        .replace("{{DESCRIPTION}}", esc(description))
        .replace("{{URL}}", url)
        .replace("{{SITE_NAME}}", esc(cfg["site_name"]))
        .replace("{{CATEGORY_SLUG}}", slug)
        .replace("{{CATEGORY_URL}}", "/%s/" % slug)
        .replace("{{CATEGORY_NAME}}", esc(cat["name"]))
        .replace("{{CATEGORY_GRID}}", grid)
        .replace("{{HEADER}}", render_header(ALL_CATEGORIES, cfg["site_name"]))
        .replace("{{FOOTER}}", render_footer(cfg["site_name"], cfg["tagline"]))
    )
    out = HTML / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print("built", out.relative_to(ROOT))


def build_homepage(categories, posts_by_category, cfg, tpl):
    title = "%s – %s" % (cfg["site_name"], cfg["tagline"])
    description = cfg["tagline"]
    sections = "\n\n".join(render_category_section(c, posts_by_category.get(c["id"], [])) for c in categories)
    if not sections:
        sections = '        <p class="empty-note">Chưa có danh mục nào.</p>'

    page = (
        tpl.replace("{{TITLE}}", esc(title))
        .replace("{{DESCRIPTION}}", esc(description))
        .replace("{{URL}}", cfg["site_url"] + "/")
        .replace("{{SITE_NAME}}", esc(cfg["site_name"]))
        .replace("{{CATEGORY_SECTIONS}}", sections)
        .replace("{{HEADER}}", render_header(categories, cfg["site_name"]))
        .replace("{{FOOTER}}", render_footer(cfg["site_name"], cfg["tagline"]))
    )
    (HTML / "index.html").write_text(page, encoding="utf-8")
    print("built html/index.html (%d danh mục)" % len(categories))


def build_sitemap(categories, posts, cfg):
    site = cfg["site_url"]
    today = max(
        [parse_iso(p["updated_at"]) for p in posts] + [parse_iso(c["created_at"]) for c in categories],
        default=datetime(2021, 1, 1, tzinfo=timezone.utc),
    ).strftime("%Y-%m-%d")

    urls = ['    <url>\n        <loc>%s/</loc>\n        <lastmod>%s</lastmod>\n        <priority>1.0</priority>\n    </url>' % (site, today)]
    for c in categories:
        urls.append(
            '    <url>\n        <loc>%s/%s/</loc>\n        <lastmod>%s</lastmod>\n        <priority>0.8</priority>\n    </url>'
            % (site, c["slug"], parse_iso(c["created_at"]).strftime("%Y-%m-%d"))
        )
    for p in posts:
        urls.append(
            '    <url>\n        <loc>%s/%s/</loc>\n        <lastmod>%s</lastmod>\n        <priority>0.6</priority>\n    </url>'
            % (site, p["slug"], parse_iso(p["updated_at"]).strftime("%Y-%m-%d"))
        )

    out = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    out += "\n".join(urls) + "\n</urlset>\n"
    (HTML / "sitemap.xml").write_text(out, encoding="utf-8")
    print("built html/sitemap.xml (1 trang chủ, %d danh mục, %d bài viết)" % (len(categories), len(posts)))


ALL_CATEGORIES = []  # duoc gan trong main(), dung lai boi build_post_page/build_category_page cho nav day du


def main():
    global ALL_CATEGORIES
    cfg = site_config()

    categories = load_json(DATA / "categories.json", [])
    categories.sort(key=lambda c: parse_iso(c["created_at"]))  # thu tu tao truoc -> sau
    ALL_CATEGORIES = categories
    categories_by_id = {c["id"]: c for c in categories}

    posts = load_json(DATA / "posts.json", [])
    # moi nhat truoc, dung cho category page + section trang chu
    posts.sort(key=lambda p: parse_iso(p["updated_at"]), reverse=True)

    posts_by_category = {}
    for p in posts:
        cat = categories_by_id.get(p.get("category_id"))
        if not cat:
            print("WARN: bài '%s' trỏ tới category_id không tồn tại — bỏ qua khỏi danh mục/trang chủ" % p["slug"])
            continue
        posts_by_category.setdefault(cat["id"], []).append(p)

    post_tpl = (TEMPLATES / "post.html").read_text(encoding="utf-8")
    category_tpl = (TEMPLATES / "category.html").read_text(encoding="utf-8")
    index_tpl = (TEMPLATES / "index.html").read_text(encoding="utf-8")

    built = 0
    for p in posts:
        cat = categories_by_id.get(p.get("category_id"))
        if not cat:
            continue
        detail_path = DATA / "posts" / p["slug"] / "detail.json"
        if not detail_path.exists():
            print("WARN: thiếu", detail_path.relative_to(ROOT), "- bỏ qua")
            continue
        build_post_page(load_json(detail_path, {}), cat, cfg, post_tpl)
        built += 1

    for cat in categories:
        build_category_page(cat, posts_by_category.get(cat["id"], []), cfg, category_tpl)

    build_homepage(categories, posts_by_category, cfg, index_tpl)
    build_sitemap(categories, posts, cfg)
    print("Done: %d danh mục, %d bài viết (%d trang bài viết đã build)" % (len(categories), len(posts), built))


if __name__ == "__main__":
    main()
