# Custom-scraper candidates

Big German employers that hire ML/AI but run on ATS platforms with **no clean
public API** (Phenom, SuccessFactors / Jobs2Web, Avature, fully proprietary).
Each one needs a bespoke scraper. BMW Group is the first done; the rest are the
backlog.

## Status

| Status | Company | Careers URL | ATS | Notes |
|---|---|---|---|---|
| ✅ done | **BMW Group** | jobs.bmwgroup.com | Jobs2Web (SF) — migrated to client-rendered; now via `Jobs2WebScraper` RSS fallback | live (RSS feed) |
| ✅ done | **adidas** | jobs.adidas-group.com | Jobs2Web (SF) `data-row` HTML via `Jobs2WebScraper` | wired; 0 German ML/DS currently (sportswear retailer) |
| ✅ done | **Allianz** | careers.allianz.com | Phenom (sitemap + JSON-LD mode) | 4 German ML/AI roles |
| ✅ done | **Bayer** | jobs.bayer.com | Phenom (Google-for-Jobs RSS mode) | 4 German ML/AI roles |
| ✅ done | **Merck KGaA** | careers.merckgroup.com | Phenom (sitemap + JSON-LD) | 1 German ML/AI role |
| ✅ done | **Procter & Gamble** | www.pgcareers.com | Phenom (sitemap + JSON-LD) | 1 German ML/AI role |
| ✅ done | **Thermo Fisher Scientific** | jobs.thermofisher.com | Phenom (sitemap + JSON-LD) | 0 currently, wired |
| ✅ done | **PwC Germany** | jobs.pwc.de | Phenom (urlset + JSON-LD) | 0 currently, wired |
| ✅ done | **Deloitte** | job.deloitte.com | Phenom (urlset + JSON-LD, `job_url_match="/job-"`) | consultancy, many German AI/Data roles |
| ✅ done | **NORD/LB** | karriere.nordlb.de | SAP SuccessFactors CSB (`SuccessFactorsScraper`, urlset + schema.org **microdata**) | 2 German KI/AI roles |
| ✅ done | **Finanz Informatik** | www.f-i.de/karriere/offene-stellen | Bespoke Netgen/Ibexa site, JSON-LD detail (`FinanzInformatikScraper` = Phenom subclass, URLs from listing page) | wired; 0 ML/DS currently (small board) |
| skip | **Microsoft** | jobs.careers.microsoft.com | Eightfold AI (not Phenom) | Different platform; would need new scraper |
| ✅ done | **Mercedes-Benz Group** | jobs.mercedes-benz.com | Nuxt site, sitemap + JSON-LD in an `@graph` wrapper (`PhenomScraper`, `job_url_match="/en/"`, 3s delay) | 15 German ML/AI roles |
| ✅ done | **Munich Re** | careers.munichre.com | Sitemap + JSON-LD, mid-path title slug (`MunichReScraper` = Phenom subclass) | 3 German ML/AI roles |
| built, disabled | **Lufthansa Group** | apply.lufthansagroup.careers | Server-rendered PHP board, sitemap + JSON-LD (`LufthansaScraper` = Phenom subclass, no slug prefilter) | Works (2 German ML/AI roles) but **not wired into `main.py`**: opaque job URLs force a fetch of all ~305 postings, ~10 min |
| todo | **Deutsche Telekom** | careers.telekom.com | Avature likely | T-Labs / AI |
| todo | **Schaeffler** | jobs.schaeffler.com | own / Phenom | Automotive components ML |
| todo | **Otto Group** | jobs.otto.de / ottogroup.com | own / SF | E-comm ML, Hamburg |
| ✅ done | **Hensoldt** | jobs.hensoldt.net | Jobs2Web (SF) via `Jobs2WebScraper` RSS fallback | 4 German AI/Data roles. The old `hensoldt.wd3.myworkdayjobs.com` Workday tenant is dead (500 at root; the 422s were not a CSRF problem) - they moved to a Jobs2Web board |
| todo | **Rheinmetall** | rheinmetall.com/career | own | Defense AI |
| todo | **E.ON** | career.eon.com | likely SAP SF | Energy ML |
| todo | **EnBW** | enbw.com/karriere | own / SF | Energy ML |
| todo | **MTU Aero Engines** | mtu.de/careers | own | Aerospace ML |
| todo | **Sartorius** | jobs.sartorius.com | own / Workday | Bioprocess ML |
| todo | **Carl Zeiss Meditec** | zeiss.de/career | own | Medical imaging |
| skip / low yield | **TeamViewer** | careers.teamviewer.com | migrated off SmartRecruiters - empty board | Investigate before retrying |

## Prioritisation

Order by expected ML/AI hiring volume + Germany concentration + scraper effort:

1. **Allianz** - Phenom. A generic Phenom scraper would also unlock Bayer, Merck
   KGaA, P&G, Thermo Fisher, PwC Germany - same family.
2. **Mercedes-Benz Group** - own ATS but very ML-active.
3. **Bayer** + **Merck KGaA** - both Phenom; come "free" if Allianz becomes a
   generic Phenom scraper.
4. **Munich Re** - reinsurance ML, sizeable Munich AI team.
5. **adidas** - retail ML; quick win if Workday tenant can be re-discovered.
6. **Lufthansa Group** - operations ML; SF makes this fiddly.
7. **Deutsche Telekom** - Avature; another platform we don't yet support.
8. Everything else - long tail.

## Notes on platform difficulty

- **Phenom People** - generic scraper now in place (`PhenomScraper`). Phenom
  tenants serve `/sitemap.xml` in one of two flavours: a Google-for-Jobs RSS
  feed with every posting inline (Bayer), or a sitemap-index whose sub-sitemaps
  list job URLs whose detail pages embed JSON-LD `JobPosting` blocks (Allianz).
  Both modes are auto-detected. New Phenom tenants only need one config line in
  `PHENOM_COMPANIES`.
- **Jobs2Web / SF** (BMW/adidas pattern) - now a generic `Jobs2WebScraper`
  (one-line config: host + name). Dual-mode: parses server-rendered
  `<tr class="data-row">` HTML at `/search?q=&startrow=` (adidas), and auto-falls
  back to the RSS feed at `/services/rss/job/?keywords=(term)` when a tenant has
  migrated to the client-rendered "searchResultsUnify" template (BMW). The RSS
  feed includes full job descriptions inline but is capped at the latest ~20
  items per keyword with no pagination, so HTML mode is preferred where available.
  Some tenants (Hensoldt) publish one opening under several requisition ids that
  differ only in the trailing digits, so the scraper also de-dupes on
  title + location before returning.
- **Avature** - server-rendered HTML; per-tenant parser needed.
- **"Sitemap + JSON-LD" is the workhorse.** Mercedes, Munich Re and Lufthansa are
  three different stacks (Nuxt, proprietary, PHP) that all reduce to the same
  `PhenomScraper` shape. Before writing anything bespoke, check `/sitemap.xml`
  and whether a detail page embeds a JSON-LD `JobPosting`. Three gotchas, all now
  handled generically: the posting may be nested in an `@graph` wrapper; the
  title slug is not always the last path segment (Munich Re) or present at all
  (Lufthansa, which needs `prefilter_by_slug = False` and fetches every posting);
  and `identifier` may be a bare string rather than a PropertyValue.
- **Bot protection.** `BaseScraper` takes `request_delay` (default 0). Mercedes
  sits behind Akamai and starts 403-ing *detail pages only* when crawled
  unthrottled - the sitemap and listing stay fine, so the symptom is "lots of
  candidates, zero jobs" rather than an obvious failure. 3s clears it. A headless
  browser is not the fix here; the block is rate-based, not fingerprint-based.
- **A JS-rendered careers page usually is not the job board.** lufthansagroup.careers
  is an Angular shell with zero links in the HTML; the real board is on the
  `apply.` subdomain and is plain server-rendered PHP. Grep the JS bundle for
  hostnames before concluding a site needs a browser.
- **Workday private tenants** - CXS endpoint can reject bodies without CSRF and
  would then need a session-bootstrap step. Before assuming that, check the
  tenant is actually alive: a uniform 422 for *every* site id (including a bogus
  one) plus a 500 at the host root means the tenant is gone and the company has
  migrated, not that auth is missing. Follow the live careers page to the real
  board first - that is what Hensoldt turned out to be.
