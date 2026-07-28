#!/usr/bin/env python3
"""
Build static HTML from data/ (run by GitHub Actions; stdlib only, no pip install needed).

Input:
  data/site.json                   # site_name / site_url / tagline / logo / banner — GAS ghi (tab "Cai dat website")
  data/categories.json             # danh muc, GAS ghi (index: id, name, slug, created_at)
  data/posts.json                  # bai viet, GAS ghi (index metadata, khong co content)
  data/posts/<slug>/detail.json    # noi dung day du 1 bai (content HTML + metadata)
  data/pages.json                  # trang tinh (gioi thieu/lien he/chinh sach...), GAS ghi
  data/pages/<slug>/detail.json    # noi dung day du 1 trang tinh — khong danh muc, khong cover
  templates/index.html, category.html, post.html, page.html
  html/<slug>/images/*             # anh da duoc GAS day thang vao day (cover + anh trong bai/trang)

Output:
  html/index.html                  # trang chu: 1 section/danh muc, theo dung thu tu tao truoc -> sau
  html/<category-slug>/index.html  # trang danh muc: toan bo bai trong danh muc, moi nhat truoc
  html/<post-slug>/index.html      # trang bai viet
  html/<page-slug>/index.html      # trang tinh — hien link o footer moi trang, thu tu tao truoc -> sau
  html/sitemap.xml                 # trang chu + moi danh muc + moi bai viet + moi trang tinh

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

HOMEPAGE_FEATURED_COUNT = 8  # section-featured: 8 bai moi nhat toan site (3 featured + 5 trending)
FEATURED_MAIN_COUNT = 3
FEATURED_ASIDE_COUNT = 5
# Cac so duoi day KHONG phai suy doan — lay dung tu CSS that trong <style> noi tuyen cua
# templates/index.html (xem html/css/homepage.css), vi CSS o do quyet dinh may bai THUC SU
# hien ra (qua :nth-child/:nth-of-type + display:none), khong phai so bai minh render ra HTML.
FIRST_CATEGORY_COUNT = 5  # .multimedia-layout .article-item:nth-of-type(n+6){display:none} -> hien dung 5
SECOND_CATEGORY_MAIN_COUNT = 3  # #page-homepage #section-lifestyle [newsfeatured] item:nth-child(n+4){display:none} -> hien dung 3
SECOND_CATEGORY_ASIDE_COUNT = 5  # #page-homepage #section-lifestyle [newstrending] item:nth-child(n+6){display:none} -> hien dung 5
RECOMMEND_COUNT = 12  # section-latest "DANH CHO BAN": bai con lai chua hien o tren
CATEGORY_LISTING_COUNT = 10  # trang danh muc: #news-latest.section-content, sau 8 bai dau (category-header)
RELATED_COUNT = 6  # trang bai viet: "BAI VIET LIEN QUAN" — toi da 6 bai CUNG danh muc, moi nhat truoc
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
        # logo: hien o vi tri logo header (fallback ve text neu chua cau hinh/chua co file).
        # banner: CHI dung lam og:image mac dinh cho trang chu/danh muc, khong hien truc tiep.
        # favicon: PNG vuong 24x24, hien trong tab trinh duyet moi trang.
        "logo": (cfg.get("logo") or "").strip().lstrip("/"),
        "banner": (cfg.get("banner") or "").strip().lstrip("/"),
        "favicon": (cfg.get("favicon") or "").strip().lstrip("/"),
    }


def favicon_tag(cfg):
    """<link rel=icon>, dung chung cho moi trang. Rong neu chua cau hinh favicon."""
    if not cfg.get("favicon"):
        return ""
    return '    <link rel="icon" type="image/png" sizes="24x24" href="/%s">' % cfg["favicon"]


def og_image_tag(cfg):
    """Meta og:image dung banner lam anh dai dien mac dinh cho trang khong co cover rieng
    (trang chu, trang danh muc). Rong neu chua cau hinh banner — khong in tag gay hieu lam."""
    if not cfg.get("banner"):
        return ""
    return '    <meta property="og:image" content="%s/%s">' % (cfg["site_url"], cfg["banner"])


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


def render_header(categories, site_name, logo=""):
    """categories da o dung thu tu tao truoc -> sau (categories.json).
    logo: duong dan tuong doi (vd "images/logo.png") -> hien <img>; rong -> fallback ve text
    (vd truoc khi file anh that duoc day vao repo)."""
    pc_cats = categories[:NAV_PC_MAX]
    overflow_cats = categories[NAV_PC_MAX:]

    pc_items = "\n".join(
        '          <li class="parent">\n'
        '            <a href="/%s/" title="%s">%s</a>\n'
        '            <div class="subcate">\n              <ul>\n              </ul>\n            </div>\n'
        '          </li>' % (c["slug"], esc(c["name"]), esc(c["name"]))
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
        '              <li class="parent">\n'
        '                <a href="/%s/" title="%s">%s</a>\n'
        '                <div class="subcate">\n                  <ul></ul>\n                </div>\n'
        '              </li>' % (c["slug"], esc(c["name"]), esc(c["name"]))
        for c in categories
    )

    logo_inner = '<img src="/%s" alt="%s">' % (logo, esc(site_name)) if logo else esc(site_name)

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
%s""" % (esc(site_name), logo_inner, pc_items, mobile_items, TOGGLE_SCRIPT)


def render_footer(site_name, tagline, pages):
    """pages: [{slug, title}], da o dung thu tu tao truoc -> sau (pages.json)."""
    if pages:
        links = "\n          ".join('<a href="/%s/">%s</a><br>' % (p["slug"], esc(p["title"])) for p in pages)
        links_block = '\n        <p style="line-height: 1.7; font-size: 12px">\n          %s\n        </p>' % links
    else:
        links_block = ""
    return """<footer id="footer">
    <div class="page-wrapper footer-wrapper">
      <div class="left-side-info">
        <div class="web-info">
          <div class="logo">%s</div>
          <p style="line-height: 1.7; font-size: 12px">%s</p>
        </div>
      </div>
      <div class="copyright-info">
        <p style="line-height: 1.7; font-size: 12px">© %s</p>%s
      </div>
    </div>
  </footer>""" % (esc(site_name), esc(tagline), esc(site_name), links_block)


# ---------- card / section renderers ----------

def render_card(post, modifier="type-text"):
    # article-summary LUON co mat (ke ca rong) — dung nguyen cau truc that trong templates/
    # (category.html, index.html): tag nay luon ton tai, CSS tu quyet dinh an/hien theo ngu canh
    # (.article-item .article-summary{display:none} mac dinh, mot so context override display:block).
    return """        <article class="article-item %s">
            <p class="article-thumbnail">
                <a href="/%s/">
                    <img src="%s" alt="%s" loading="lazy">
                </a>
            </p>
            <header>
                <p class="article-title">
                    <a href="/%s/">%s</a>
                </p>
                <p class="article-summary">%s</p>
            </header>
        </article>""" % (
        modifier, post["slug"], cover_of(post), esc(post["title"]), post["slug"], esc(post["title"]),
        esc(truncate(post.get("description", "")))
    )


def empty_note():
    return '            <p class="empty-note">Chưa có bài viết trong danh mục này.</p>'


def render_featured_section(top_posts):
    """8 bai moi nhat toan site (khong theo danh muc): 3 bai lon (picked-featured)
    + 5 bai nho ben canh (picked-trending), giong het section-featured cua templates/index.html."""
    if not top_posts:
        return ""
    featured = top_posts[:FEATURED_MAIN_COUNT]
    trending = top_posts[FEATURED_MAIN_COUNT:FEATURED_MAIN_COUNT + FEATURED_ASIDE_COUNT]
    featured_html = "\n".join(render_card(p, "znews-native type-text picked-featured") for p in featured) or empty_note()
    trending_html = "\n".join(render_card(p, "type-text picked-trending short") for p in trending)
    return """        <section id="section-featured" class="section">
            <div class="section-content">
                <div data-content="newsfeatured" class="article-list" id="list-first">
%s
                </div>
                <div data-content="newstrending" class="article-list listing-layout" id="list-second">
%s
                </div>
            </div>
        </section>""" % (featured_html, trending_html)


def render_first_category_section(cat, posts_in_cat):
    """Danh muc dau tien: nen vang (#section-multimedia co ::before mau #ffde76 trong
    page_common.css), toi da 5 bai (xem FIRST_CATEGORY_COUNT), layout multimedia-layout (bai dau to, giua trang)."""
    shown = posts_in_cat[:FIRST_CATEGORY_COUNT]
    grid = "\n".join(render_card(p, "znews-native type-picture picked-multi short") for p in shown) or empty_note()
    return """        <section id="section-multimedia" class="section first-category">
            <header class="section-title">
                <h2>%s</h2>
            </header>
            <div class="section-content">
                <div class="article-list multimedia-layout" id="list-first-category">
%s
                </div>
                <div class="article-list" id="list-first-category-aside"></div>
            </div>
        </section>""" % (esc(cat["name"]), grid)


def render_recommend_section(posts):
    """section-latest "DANH CHO BAN": nhung bai con lai chua hien o section-featured/first-category."""
    shown = posts[:RECOMMEND_COUNT]
    if not shown:
        return ""
    grid = "\n".join(render_card(p, "type-text") for p in shown)
    return """        <section id="section-latest" class="section has-sidebar">
            <header class="section-title">
                <h3>DÀNH CHO BẠN</h3>
            </header>
            <section class="section-content">
                <div class="article-list listing-layout responsive unique" id="list-recommend">
%s
                </div>
                <aside class="section-sidebar"></aside>
            </section>
        </section>""" % grid


def render_related_section(related_posts):
    """Trang bai viet, cuoi trang: "BAI VIET LIEN QUAN" — giong het #article-nextreads >
    #news-latest.section.has-sidebar cua cau-hinh-toi-thieu-....html. related_posts = toi da
    6 bai CUNG danh muc voi bai dang xem (tu build_post_page), moi nhat truoc."""
    if not related_posts:
        return ""
    grid = "\n".join(render_card(p, "znews-native type-text picked-featured") for p in related_posts)
    return """    <div id="article-nextreads" class="">
    <div id="trending" class="page-wrapper">
        <section id="news-latest" class="section has-sidebar">
            <header class="section-title">
                <h2>BÀI VIẾT LIÊN QUAN</h2>
            </header>
            <section class="section-content">
                <div class="article-list listing-layout responsive infinite-load" id="news-reference">
%s
                </div>
                <aside class="section-sidebar"></aside>
            </section>
        </section>
    </div>
    </div>""" % grid


def render_second_category_section(cat, posts_in_cat):
    """Danh muc thu 2 tro di: cot chinh toi da 8 bai + cot phu (aside) toi da 5 bai tiep theo,
    giong het section-lifestyle (class second-category) cua templates/index.html."""
    main = posts_in_cat[:SECOND_CATEGORY_MAIN_COUNT]
    aside = posts_in_cat[SECOND_CATEGORY_MAIN_COUNT:SECOND_CATEGORY_MAIN_COUNT + SECOND_CATEGORY_ASIDE_COUNT]
    main_html = "\n".join(render_card(p, "znews-native type-text") for p in main) or empty_note()
    aside_html = "\n".join(render_card(p, "znews-native type-text") for p in aside)
    return """      <section id="section-lifestyle" class="section second-category">
        <header class="section-title">
          <h2>%s</h2>
        </header>
        <div class="section-content ">
          <div class="article-list lifestyle-layout" data-content="newsfeatured" id="list-second-category">
%s
          </div>
          <div class="article-list" data-content="newstrending" id="list-second-category-aside">
%s
          </div>
        </div>
      </section>""" % (esc(cat["name"]), main_html, aside_html)


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

def build_post_page(detail, cat, posts, cfg, tpl):
    """posts: TOAN BO bai viet (da sap moi nhat truoc, tu main()) — dung de tinh 'BAI VIET LIEN QUAN'."""
    slug = detail["slug"]
    url = "%s/%s/" % (cfg["site_url"], slug)
    # og:image/JSON-LD: uu tien cover that cua bai; khong co thi fallback ve banner site (KHONG
    # dung placeholder SVG noi bo — anh dai dien MXH phai la anh that hoac khong co gi ca).
    image_path = detail.get("cover") or cfg.get("banner")
    image_url = "%s/%s" % (cfg["site_url"], image_path) if image_path else None
    description = truncate(detail.get("description") or strip_html(detail.get("content", "")), 220)
    published_iso = detail.get("created_at") or ""

    json_ld_obj = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "headline": detail["title"],
        "description": description,
        "datePublished": published_iso,
        "dateModified": detail.get("updated_at") or published_iso,
        "author": {"@type": "Organization", "name": cfg["site_name"]},
        "publisher": {"@type": "Organization", "name": cfg["site_name"]},
    }
    if image_url:
        json_ld_obj["image"] = [image_url]
    json_ld = json.dumps(json_ld_obj, ensure_ascii=False, indent=2)

    og_image = '    <meta property="og:image" content="%s">' % image_url if image_url else ""

    # "BAI VIET LIEN QUAN": toi da 6 bai CUNG danh muc voi bai dang xem, moi nhat truoc, tru
    # chinh no. posts da duoc main() sap moi nhat truoc san nen chi can loc + cat dau.
    related = [p for p in posts if p.get("category_id") == cat["id"] and p["slug"] != slug][:RELATED_COUNT]

    page = (
        tpl.replace("{{TITLE}}", esc(detail["title"]))
        .replace("{{DESCRIPTION}}", esc(description))
        .replace("{{URL}}", url)
        .replace("{{SITE_NAME}}", esc(cfg["site_name"]))
        .replace("{{OG_IMAGE_TAG}}", og_image)
        .replace("{{FAVICON_TAG}}", favicon_tag(cfg))
        .replace("{{PUBLISHED_ISO}}", esc(published_iso))
        .replace("{{JSON_LD}}", json_ld)
        .replace("{{CATEGORY_URL}}", "/%s/" % cat["slug"])
        .replace("{{CATEGORY_NAME}}", esc(cat["name"]))
        .replace("{{DATE_DISPLAY}}", date_display(published_iso))
        .replace("{{CONTENT}}", transform_content(detail.get("content", ""), slug))
        .replace("{{RELATED_SECTION}}", render_related_section(related))
        .replace("{{HEADER}}", render_header(ALL_CATEGORIES, cfg["site_name"], cfg["logo"]))
        .replace("{{FOOTER}}", render_footer(cfg["site_name"], cfg["tagline"], ALL_PAGES))
    )
    out = HTML / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print("built", out.relative_to(ROOT))


def build_category_page(cat, posts_in_cat, cfg, tpl):
    """Bam sat am-thuc.html that: giong het khoi "8 bai chinh" cua trang chu (3 featured +
    5 trending, nhung gioi han trong CHINH danh muc nay, khong tron danh muc khac), roi toi
    #news-latest.section-content rieng cho 10 bai tiep theo. Khac trang chu: co ten danh muc,
    KHONG co cac section "danh muc khac"."""
    slug = cat["slug"]
    url = "%s/%s/" % (cfg["site_url"], slug)
    title = "%s – %s" % (cat["name"], cfg["site_name"])
    description = "Toàn bộ bài viết thuộc danh mục %s trên %s." % (cat["name"], cfg["site_name"])

    featured = posts_in_cat[:FEATURED_MAIN_COUNT]
    trending = posts_in_cat[FEATURED_MAIN_COUNT:FEATURED_MAIN_COUNT + FEATURED_ASIDE_COUNT]
    more = posts_in_cat[
        FEATURED_MAIN_COUNT + FEATURED_ASIDE_COUNT:
        FEATURED_MAIN_COUNT + FEATURED_ASIDE_COUNT + CATEGORY_LISTING_COUNT
    ]

    featured_html = "\n".join(render_card(p, "znews-native type-text picked-featured") for p in featured) or empty_note()
    trending_html = "\n".join(render_card(p, "type-text picked-trending short") for p in trending)
    more_html = "\n".join(render_card(p) for p in more)

    page = (
        tpl.replace("{{TITLE}}", esc(title))
        .replace("{{DESCRIPTION}}", esc(description))
        .replace("{{URL}}", url)
        .replace("{{SITE_NAME}}", esc(cfg["site_name"]))
        .replace("{{CATEGORY_SLUG}}", slug)
        .replace("{{CATEGORY_URL}}", "/%s/" % slug)
        .replace("{{CATEGORY_NAME}}", esc(cat["name"]))
        .replace("{{CATEGORY_FEATURED}}", featured_html)
        .replace("{{CATEGORY_TRENDING}}", trending_html)
        .replace("{{CATEGORY_MORE}}", more_html)
        .replace("{{OG_IMAGE_TAG}}", og_image_tag(cfg))
        .replace("{{FAVICON_TAG}}", favicon_tag(cfg))
        .replace("{{HEADER}}", render_header(ALL_CATEGORIES, cfg["site_name"], cfg["logo"]))
        .replace("{{FOOTER}}", render_footer(cfg["site_name"], cfg["tagline"], ALL_PAGES))
    )
    out = HTML / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print("built", out.relative_to(ROOT))


def build_page(page, cfg, tpl):
    """Trang tinh (gioi thieu/lien he/chinh sach...) — khong danh muc, khong cover."""
    slug = page["slug"]
    url = "%s/%s/" % (cfg["site_url"], slug)
    description = truncate(strip_html(page.get("content", "")), 220)

    json_ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "@id": url,
            "name": page["title"],
            "description": description,
            "url": url,
            "isPartOf": {"@type": "WebSite", "name": cfg["site_name"], "url": cfg["site_url"] + "/"},
        },
        ensure_ascii=False,
        indent=2,
    )

    rendered = (
        tpl.replace("{{TITLE}}", esc(page["title"]))
        .replace("{{DESCRIPTION}}", esc(description))
        .replace("{{URL}}", url)
        .replace("{{SITE_NAME}}", esc(cfg["site_name"]))
        .replace("{{OG_IMAGE_TAG}}", og_image_tag(cfg))
        .replace("{{FAVICON_TAG}}", favicon_tag(cfg))
        .replace("{{JSON_LD}}", json_ld)
        .replace("{{CONTENT}}", transform_content(page.get("content", ""), slug))
        .replace("{{HEADER}}", render_header(ALL_CATEGORIES, cfg["site_name"], cfg["logo"]))
        .replace("{{FOOTER}}", render_footer(cfg["site_name"], cfg["tagline"], ALL_PAGES))
    )
    out = HTML / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    print("built", out.relative_to(ROOT))


def build_homepage(categories, posts, posts_by_category, cfg, tpl):
    """Bo cuc trang chu bam sat templates/index.html:
    - 1 page-wrapper dau: section-featured (8 bai moi nhat toan site)
      + section-multimedia (danh muc dau tien, nen vang, toi da 5 bai)
      + section-latest "DANH CHO BAN" (12 bai moi nhat tiep theo, TINH THEO VI TRI
        sau 8 bai dau — khong loai tru bai da xuat hien o section-multimedia, dung
        nhu templates/index.html: cac khoi widget doc lap, khong dedup lan nhau)
    - Moi danh muc con lai: 1 page-wrapper rieng, section-lifestyle (second-category)."""
    title = "%s – %s" % (cfg["site_name"], cfg["tagline"])
    description = cfg["tagline"]

    top_group = []

    featured_posts = posts[:HOMEPAGE_FEATURED_COUNT]
    featured_section = render_featured_section(featured_posts)
    if featured_section:
        top_group.append(featured_section)

    first_cat, rest_cats = (categories[0], categories[1:]) if categories else (None, [])
    if first_cat:
        first_cat_posts = posts_by_category.get(first_cat["id"], [])
        top_group.append(render_first_category_section(first_cat, first_cat_posts))

    remaining_posts = posts[HOMEPAGE_FEATURED_COUNT:HOMEPAGE_FEATURED_COUNT + RECOMMEND_COUNT]
    recommend_section = render_recommend_section(remaining_posts)
    if recommend_section:
        top_group.append(recommend_section)

    blocks = []
    if top_group:
        blocks.append('    <div class="page-wrapper">\n' + "\n".join(top_group) + "\n    </div>")
    for cat in rest_cats:
        section = render_second_category_section(cat, posts_by_category.get(cat["id"], []))
        blocks.append('      <div class="page-wrapper">\n' + section + "\n      </div>")

    sections = "\n".join(blocks)
    if not sections:
        sections = '    <p class="empty-note">Chưa có danh mục nào.</p>'

    page = (
        tpl.replace("{{TITLE}}", esc(title))
        .replace("{{DESCRIPTION}}", esc(description))
        .replace("{{URL}}", cfg["site_url"] + "/")
        .replace("{{SITE_NAME}}", esc(cfg["site_name"]))
        .replace("{{CATEGORY_SECTIONS}}", sections)
        .replace("{{OG_IMAGE_TAG}}", og_image_tag(cfg))
        .replace("{{FAVICON_TAG}}", favicon_tag(cfg))
        .replace("{{HEADER}}", render_header(categories, cfg["site_name"], cfg["logo"]))
        .replace("{{FOOTER}}", render_footer(cfg["site_name"], cfg["tagline"], ALL_PAGES))
    )
    (HTML / "index.html").write_text(page, encoding="utf-8")
    print("built html/index.html (%d danh mục)" % len(categories))


def build_sitemap(categories, posts, pages, cfg):
    site = cfg["site_url"]
    today = max(
        [parse_iso(p["updated_at"]) for p in posts]
        + [parse_iso(c["created_at"]) for c in categories]
        + [parse_iso(pg["updated_at"]) for pg in pages],
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
    for pg in pages:
        urls.append(
            '    <url>\n        <loc>%s/%s/</loc>\n        <lastmod>%s</lastmod>\n        <priority>0.3</priority>\n    </url>'
            % (site, pg["slug"], parse_iso(pg["updated_at"]).strftime("%Y-%m-%d"))
        )

    out = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    out += "\n".join(urls) + "\n</urlset>\n"
    (HTML / "sitemap.xml").write_text(out, encoding="utf-8")
    print("built html/sitemap.xml (1 trang chủ, %d danh mục, %d bài viết, %d trang tĩnh)" % (len(categories), len(posts), len(pages)))


ALL_CATEGORIES = []  # duoc gan trong main(), dung lai boi build_post_page/build_category_page cho nav day du
ALL_PAGES = []  # duoc gan trong main(), dung lai boi moi render_footer() cho link trang tinh day du


def main():
    global ALL_CATEGORIES, ALL_PAGES
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

    pages = load_json(DATA / "pages.json", [])
    pages.sort(key=lambda pg: parse_iso(pg["created_at"]))  # thu tu tao truoc -> sau, khop footer
    ALL_PAGES = pages

    post_tpl = (TEMPLATES / "post.html").read_text(encoding="utf-8")
    category_tpl = (TEMPLATES / "category.html").read_text(encoding="utf-8")
    index_tpl = (TEMPLATES / "index.html").read_text(encoding="utf-8")
    page_tpl = (TEMPLATES / "page.html").read_text(encoding="utf-8")

    built = 0
    for p in posts:
        cat = categories_by_id.get(p.get("category_id"))
        if not cat:
            continue
        detail_path = DATA / "posts" / p["slug"] / "detail.json"
        if not detail_path.exists():
            print("WARN: thiếu", detail_path.relative_to(ROOT), "- bỏ qua")
            continue
        build_post_page(load_json(detail_path, {}), cat, posts, cfg, post_tpl)
        built += 1

    for cat in categories:
        build_category_page(cat, posts_by_category.get(cat["id"], []), cfg, category_tpl)

    built_pages = 0
    for pg in pages:
        detail_path = DATA / "pages" / pg["slug"] / "detail.json"
        if not detail_path.exists():
            print("WARN: thiếu", detail_path.relative_to(ROOT), "- bỏ qua")
            continue
        build_page(load_json(detail_path, {}), cfg, page_tpl)
        built_pages += 1

    build_homepage(categories, posts, posts_by_category, cfg, index_tpl)
    build_sitemap(categories, posts, pages, cfg)
    print(
        "Done: %d danh mục, %d bài viết (%d đã build), %d trang tĩnh (%d đã build)"
        % (len(categories), len(posts), built, len(pages), built_pages)
    )


if __name__ == "__main__":
    main()
