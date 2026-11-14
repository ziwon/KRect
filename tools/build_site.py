#!/usr/bin/env python3
"""Build KRect's localized static landing pages without package dependencies."""
import html
import json
from pathlib import Path
import re
import shutil
from string import Template
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site"
OUTPUT = ROOT / "dist/site"
REPO = "https://github.com/ziwon/KRect"


def build():
    config = json.loads((SOURCE / "config.json").read_text())
    origin = config["origin"].rstrip("/")
    if not re.fullmatch(r"https://[a-z0-9.-]+", origin):
        raise ValueError("origin must be an HTTPS site origin without a path")
    release = config["release"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", release):
        raise ValueError("release must be a published semantic version")
    template = Template((SOURCE / "template.html").read_text())
    locales = {"ko": ("/", "한국어", "ko_KR", "README.md"),
               "en": ("/en/", "English", "en_US", "README.en.md"),
               "ja": ("/ja/", "日本語", "ja_JP", "README.ja.md")}
    translations = {lang: json.loads((SOURCE / f"locales/{lang}.json").read_text()) for lang in locales}
    if any(copy.keys() != translations["ko"].keys() for copy in translations.values()):
        raise ValueError("All locales must contain the same translation keys")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE / "assets", OUTPUT / "assets", dirs_exist_ok=True)
    for name in ("icon.svg", "layouts.png"):
        shutil.copyfile(ROOT / "assets/readme" / name, OUTPUT / "assets" / name)
    verification = config.get("google_site_verification")
    meta = f'<meta name="google-site-verification" content="{html.escape(verification, quote=True)}">' if verification else ""
    release_url = f"{REPO}/releases/tag/v{release}"
    download_base = f"{REPO}/releases/download/v{release}"
    for lang, copy in translations.items():
        home, label, og_locale, readme = locales[lang]
        values = {key: html.escape(value, quote=True) for key, value in copy.items()}
        values.update({
            "lang": lang, "home": home, "origin": origin, "canonical": origin + home,
            "language_nav": "\n      ".join(f'<a href="{path}" lang="{code}" hreflang="{code}">{name}</a>'
                                                 for code, (path, name, _, _) in locales.items() if code != lang),
            "og_locale": og_locale,
            "release": release, "release_url": release_url,
            "deb_24": f"{download_base}/krect_{release}-1ubuntu24.04_all.deb",
            "deb_26": f"{download_base}/krect_{release}-1ubuntu26.04_all.deb",
            "readme_url": f"{REPO}/blob/main/{readme}",
            "validation_url": f"{REPO}/blob/v{release}/docs/VALIDATION.md",
            "verification_meta": meta,
        })
        schema = {
            "@context": "https://schema.org", "@type": "SoftwareApplication",
            "name": "KRect", "url": origin + home, "description": copy["description"],
            "applicationCategory": "UtilitiesApplication", "operatingSystem": "Linux, KDE Plasma 5.27 or 6",
            "softwareVersion": release, "inLanguage": ["ko", "en"],
            "license": f"{REPO}/blob/main/LICENSE", "isAccessibleForFree": True,
            "downloadUrl": release_url, "screenshot": origin + "/assets/layouts.png",
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD", "url": origin + home + "#download"},
        }
        values["structured_data"] = json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c")
        target = OUTPUT / home.lstrip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(template.substitute(values))
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    xhtml = "http://www.w3.org/1999/xhtml"
    ET.register_namespace("", namespace)
    ET.register_namespace("xhtml", xhtml)
    sitemap = ET.Element(f"{{{namespace}}}urlset")
    for path, _, _, _ in locales.values():
        entry = ET.SubElement(sitemap, f"{{{namespace}}}url")
        ET.SubElement(entry, f"{{{namespace}}}loc").text = origin + path
        for code, (locale_path, _, _, _) in locales.items():
            ET.SubElement(entry, f"{{{xhtml}}}link", rel="alternate", hreflang=code, href=origin + locale_path)
        ET.SubElement(entry, f"{{{xhtml}}}link", rel="alternate", hreflang="x-default", href=origin + "/")
    ET.ElementTree(sitemap).write(OUTPUT / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    (OUTPUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {origin}/sitemap.xml\n")
    (OUTPUT / "_headers").write_text("/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  Permissions-Policy: camera=(), microphone=(), geolocation=()\n/assets/fonts/*\n  Cache-Control: public, max-age=31536000, immutable\n")
    (OUTPUT / "404.html").write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex"><title>페이지를 찾을 수 없습니다 · KRect</title><link rel="stylesheet" href="/assets/site.css"><main class="wrap questions"><h1>페이지를 찾을 수 없습니다.</h1><p>Page not found.</p><a class="button primary" href="/">KRect 홈 / Home</a></main></html>')
    print(f"Built Korean, English and Japanese pages, sitemap, robots, and app schema in {OUTPUT}")


if __name__ == "__main__":
    build()
