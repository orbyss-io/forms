"""Public initial-HTML rendering and machine-readable views from one validated content model."""
from __future__ import annotations

import html
import json
import re
from xml.etree import ElementTree as ET

from ui_contracts import discoverable, public
from ui_svg import icon_markup


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def json_script(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def absolute(origin: str, url: str) -> str:
    return origin + url if url.startswith("/") else url


def facts(page: dict) -> list[str]:
    result = []
    if "article" in page:
        result.append(f"By {page['article']['author']}. Published {page['article']['datePublished']}. Updated {page['lastModified']}.")
    if "product" in page:
        p = page["product"]
        result.append(f"{p['price']} {p['currency']} per {p['unit']}. Region: {p['region']}. {p['terms']}")
    return result


def structured_data(page: dict, origin: str) -> dict:
    entity = {"@context": "https://schema.org", "@type": "WebPage", "url": origin + page["path"],
              "name": page["title"], "description": page["description"], "inLanguage": page["language"],
              "dateModified": page["lastModified"]}
    if "image" in page:
        entity["image"] = absolute(origin, page["image"]["url"])
    if "article" in page:
        entity.update({"@type": "Article", "headline": page["title"], "author": {"@type": page["article"]["authorType"], "name": page["article"]["author"]},
                       "datePublished": page["article"]["datePublished"]})
    if "product" in page:
        p = page["product"]
        entity.update({"@type": p["type"], "offers": {"@type": "Offer", "url": origin + page["path"],
                       "price": p["price"], "priceCurrency": p["currency"], "description": facts(page)[0],
                       "eligibleRegion": p["region"], "priceSpecification": {"@type": "UnitPriceSpecification",
                           "price": p["price"], "priceCurrency": p["currency"], "unitText": p["unit"]}}})
    return entity


def head(page: dict, content: dict, profile: dict) -> str:
    origin = content["origin"]
    canonical = origin + page["path"]
    lines = ['<meta charset="utf-8">', '<meta name="viewport" content="width=device-width, initial-scale=1">',
             f"<title>{esc(page['title'])}</title>", f'<meta name="description" content="{esc(page["description"])}">',
             f'<link rel="canonical" href="{esc(canonical)}">',
             f'<meta name="robots" content="{"index,follow" if page["index"] else "noindex,follow"}">']
    for name, value in (("og:title", page["title"]), ("og:description", page["description"]), ("og:url", canonical),
                        ("og:type", "article" if "article" in page else "website")):
        lines.append(f'<meta property="{name}" content="{esc(value)}">')
    if "image" in page:
        lines += [f'<meta property="og:image" content="{esc(absolute(origin, page["image"]["url"]))}">',
                  f'<meta property="og:image:alt" content="{esc(page["image"]["alt"])}">']
    if "favicon" in profile["brand"]:
        lines.append(f'<link rel="icon" href="{esc(profile["brand"]["favicon"])}">')
    if page.get("alternates"):
        alternatives = [p for p in content["pages"] if p["id"] in [page["id"], *page["alternates"]]]
        for other in alternatives:
            lines.append(f'<link rel="alternate" hreflang="{other["language"]}" href="{esc(origin + other["path"])}">')
    if discoverable(page) and profile["discovery"]["markdown"]:
        lines.append(f'<link rel="alternate" type="text/markdown" href="{esc(origin)}/discovery/{page["id"]}.md">')
    if discoverable(page) and profile["discovery"]["llms"]:
        lines.append('<link rel="describedby" type="text/markdown" href="/llms.txt">')
    lines += ['<link rel="stylesheet" href="/assets/tokens.css">', '<link rel="stylesheet" href="/assets/layout.css">',
              f'<script type="application/ld+json">{json_script(structured_data(page, origin))}</script>']
    return "\n".join(lines)


def block_html(block: dict) -> str:
    kind = block["type"]
    if kind == "heading":
        return f'<h2 id="{block["id"]}">{esc(block["text"])}</h2>'
    if kind == "paragraph":
        return f'<p>{esc(block["text"])}</p>'
    if kind == "link":
        return f'<p><a href="{esc(block["url"])}">{esc(block["text"])}</a></p>'
    if kind == "list":
        return '<ul>' + ''.join(f'<li>{esc(item)}</li>' for item in block["items"]) + '</ul>'
    headers = ''.join(f'<th scope="col">{esc(item)}</th>' for item in block["headers"])
    rows = ''.join('<tr>' + ''.join(f'<td>{esc(item)}</td>' for item in row) + '</tr>' for row in block["rows"])
    return f'<div class="pk-table" role="region" aria-label="{esc(block["text"])}" tabindex="0"><table><caption>{esc(block["text"])}</caption><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table></div>'


def document(page: dict, content: dict, profile: dict, extra_body: str = "", extra_head: str = "") -> str:
    links = []
    if profile["navigation"] == "contextual":
        links = [f'<li><a href="#{block["id"]}">{esc(block["text"])}</a></li>' for block in page["blocks"] if block["type"] == "heading"]
    elif profile["navigation"] != "none":
        for other in content["pages"]:
            if public(other):
                current = ' aria-current="page"' if page["id"] == other["id"] else ''
                links.append(f'<li><a href="{esc(other["path"])}"{current}>{esc(other["title"])}</a></li>')
    navigation = '<nav class="pk-nav" aria-label="Primary"><ul>' + ''.join(links) + '</ul></nav>' if links else ''
    brand = esc(profile["brand"]["name"])
    if "logo" in profile["brand"]:
        logo = profile["brand"]["logo"]
        brand = f'<img src="{esc(logo.get("url", "/assets/brand-logo.svg"))}" alt="{esc(logo["alt"])}">'
    sections = "\n".join(block_html(block) for block in page["blocks"])
    visible_facts = ''.join(f'<p>{esc(fact)}</p>' for fact in facts(page))
    return f'''<!doctype html>
<html lang="{page['language']}" dir="{page.get('direction', 'ltr')}">
<head>{head(page, content, profile)}{extra_head}</head>
<body data-archetype="{profile['archetype']}" data-navigation="{profile['navigation']}">
<a class="pk-skip" href="#main" tabindex="0">Skip to content</a>
<header class="pk-header"><a class="pk-brand" href="/">{brand}</a></header>
<div class="pk-shell">{navigation}<main id="main" tabindex="-1"><div class="pk-content">
<h1 id="page-title">{esc(page['title'])}</h1><p>{esc(page['description'])}</p>
{visible_facts}{sections}{extra_body}
</div></main></div>
<footer class="pk-footer">{esc(profile['brand']['name'])}</footer>
</body></html>
'''


def markdown(page: dict, origin: str) -> str:
    def md(value: str) -> str:
        value = html.escape(value, quote=False).replace("\n", " ").replace("\r", " ")
        return re.sub(r"([\\`*_{}\[\]()#+|~-])", r"\\\1", value)
    lines = [f"# {md(page['title'])}", f"Canonical: <{origin + page['path']}>", md(page["description"]), *map(md, facts(page))]
    for block in page["blocks"]:
        if block["type"] == "heading":
            lines.append("## " + md(block["text"]))
        elif block["type"] == "paragraph":
            lines.append(md(block["text"]))
        elif block["type"] == "link":
            # Percent-encode Markdown delimiters without changing URL semantics.
            url = absolute(origin, block["url"]).replace("(", "%28").replace(")", "%29")
            lines.append(f"[{md(block['text'])}]({url})")
        elif block["type"] == "list":
            lines.append("\n".join("- " + md(item) for item in block["items"]))
        else:
            lines.append(md(block["text"]))
            rows = [block["headers"], ["---"] * len(block["headers"]), *block["rows"]]
            lines.append("\n".join("| " + " | ".join(md(item) if index != 1 else item for item in row) + " |" for index, row in enumerate(rows)))
    return "\n\n".join(lines) + "\n"


def discovery(content: dict, profile: dict) -> dict[str, str]:
    origin = content["origin"]
    pages = [page for page in content["pages"] if discoverable(page)]
    settings = profile["discovery"]
    # Explicit groups avoid robots' most-specific-agent group replacing a wildcard unexpectedly.
    robots = ["# Policy preferences, not authentication. Provider behavior differs."]
    groups = [("*", settings["search"]), ("Googlebot", settings["search"]),
              ("bingbot", settings["search"]), ("OAI-SearchBot", settings["search"]),
              ("Claude-SearchBot", settings["search"]), ("PerplexityBot", settings["search"]),
              ("GPTBot", settings["training"]), ("ClaudeBot", settings["training"]),
              ("Google-Extended", settings["training"]), ("ChatGPT-User", settings["userFetch"]),
              ("Claude-User", settings["userFetch"]), ("Perplexity-User", settings["userFetch"])]
    for agent, allowed in groups:
        robots += [f"User-agent: {agent}", "Disallow:" if allowed else "Disallow: /", ""]
    robots.append(f"Sitemap: {origin}/sitemap.xml")
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    root = ET.Element(f"{{{ns}}}urlset")
    for page in pages:
        item = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(item, f"{{{ns}}}loc").text = origin + page["path"]
        ET.SubElement(item, f"{{{ns}}}lastmod").text = page["lastModified"]
    result = {"robots.txt": "\n".join(robots) + "\n", "sitemap.xml": ET.tostring(root, encoding="unicode", xml_declaration=True) + "\n"}
    if settings["markdown"]:
        result.update({f"discovery/{page['id']}.md": markdown(page, origin) for page in pages})
    if settings["llms"]:
        result["llms.txt"] = f"# {esc(profile['brand']['name'])}\n\n> Optional public content index. Canonical HTML remains authoritative.\n\n## Pages\n\n" + "\n".join(
            f"- [{page['id']}]({origin}/discovery/{page['id']}.md)" for page in pages) + "\n"
    return result


def gallery(profile: dict) -> str:
    page = {"id": "gallery", "path": "/", "intent": "public-utility", "index": False,
            "title": "Component acceptance gallery", "description": "Test states and keyboard behavior; not a consumer journey.",
            "language": "en", "lastModified": "2026-09-05", "blocks": []}
    body = '''<div class="pk-cards">
<section class="pk-card pk-stack" aria-labelledby="actions"><h2 id="actions">Actions</h2>
<button type="button" data-pk-dialog="confirm">Open confirmation</button>
<button type="button" disabled>Unavailable action</button>
<button type="button" aria-busy="true" disabled>Saving…</button></section>
<section class="pk-card pk-stack" aria-labelledby="fields"><h2 id="fields">Form feedback</h2>
<label for="email">Email address</label><input id="email" type="email" autocomplete="email" aria-invalid="true" aria-describedby="email-error">
<p id="email-error" class="pk-error">Enter a valid email address.</p></section>
<section class="pk-card" aria-labelledby="states"><h2 id="states">Content states</h2>
<p>No items yet. Create your first item to begin.</p><p role="status" class="pk-status">Saved successfully.</p>
<p role="alert" class="pk-error">Could not save. Your input is preserved; try again.</p></section>
</div>
<dialog id="confirm" aria-labelledby="confirm-title"><h2 id="confirm-title">Confirm action</h2>
<p>Escape or Cancel closes this dialog and returns focus.</p><form method="dialog"><button autofocus>Cancel</button></form></dialog>'''
    body += '<section aria-labelledby="icons"><h2 id="icons">Icon semantics</h2><p>' + icon_markup(profile, "check") + ' Saved (decorative icon with visible text)</p><button type="button" aria-label="Search">' + icon_markup(profile, "search") + ' Search</button></section>'
    return document(page, {"origin": "https://example.invalid", "pages": [page]}, profile, body,
                    '<script type="module" src="/assets/interactions.mjs"></script>')
