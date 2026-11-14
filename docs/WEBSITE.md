# KRect website

The public landing page is hosted on Cloudflare Pages at **https://krect.pages.dev**.
Korean is at `/`, English at `/en/`, and Japanese at `/ja/`. All three are complete static HTML documents,
so downloads and readable content remain available without JavaScript.

## Build and deploy

```bash
python3 tools/build_site.py
python3 -m http.server 8789 --directory dist/site
wrangler pages deploy dist/site --project-name krect --branch main
```

The build needs only Python's standard library. Wrangler requires a Cloudflare
login with access to the `krect` Pages project. Deploy **only `dist/site`**.
The first deployment uses Direct Upload; no GitHub Actions credentials are stored
in the repository. See [Cloudflare Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/).

Source files:

- `site/template.html`: semantic markup and the paper/page-curl design contract.
- `site/locales/{ko,en,ja}.json`: matching Korean, English and Japanese copy.
- `site/assets/`: shared CSS, interaction code, self-hosted SUIT font and license.
- `site/config.json`: public origin, published release version and optional Search Console verification token.
- `tools/build_site.py`: localized HTML, screenshot/icon copies, sitemap, robots,
  application structured data, response headers and a real 404 page.

The app screenshot is copied unchanged from `assets/readme/layouts.png`. The
landscape and portrait snap bar captures come from the isolated live validation
client. Every capture carries its origin in a JSON sidecar. SUIT is distributed under its included OFL license.
Prepare the release version in `site/config.json` with the matching application
release, and deploy the site only after the corresponding GitHub assets exist.

## Free downloads

The page links directly to the selected Ubuntu `.deb` on GitHub Releases.
KRect is free and MIT-licensed. There are no prices, checkout links, payment
providers, account requirements or feature gates on the landing page.

## Search and sharing

Each locale has its own title, description, canonical URL, reciprocal `hreflang`
links and Open Graph/Twitter metadata. The builder emits `sitemap.xml`,
`robots.txt` and truthful `SoftwareApplication` JSON-LD with a free offer.
No reviews, ratings, download counts or search rankings are invented.

To manage indexing in Google Search Console:

1. Add the URL-prefix property `https://krect.pages.dev/`.
2. Choose HTML-tag verification. Put only the token's `content` value in
   `google_site_verification` in `site/config.json`, rebuild and deploy, then verify.
3. Submit `https://krect.pages.dev/sitemap.xml` and inspect `/`, `/en/`, and `/ja/`.

Google decides whether and when to index the pages. Shipping metadata and a sitemap
does not mean indexing has happened or guarantee a rich result. No Search Console
ownership verification or indexing request has been completed by this build.

The static 404 document prevents missing URLs from becoming indexable copies of
the homepage. Cloudflare preview deployments should remain excluded from indexing;
verify the platform's `X-Robots-Tag: noindex` header before sharing a preview URL.

- [Google: localized pages](https://developers.google.com/search/docs/specialty/international/localized-versions)
- [Google: building a sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)

The website and README support Korean, English and Japanese. The native app UI
currently supports Korean and English; the Japanese page states this explicitly.
Japanese glyphs use the configured Noto CJK/Hiragino/Meiryo fallbacks alongside SUIT.
