# Custom-scraper candidates

Big German employers that hire ML/AI but run on ATS platforms with **no clean
public API** (Phenom, SuccessFactors / Jobs2Web, Avature, fully proprietary).
Each one needs a bespoke scraper. BMW Group is the first done; the rest are the
backlog.

## Status

| Status | Company | Careers URL | ATS | Notes |
|---|---|---|---|---|
| ✅ done | **BMW Group** | jobs.bmwgroup.com | Jobs2Web (SF front-end) HTML | 28 German ML/AI roles |
| ✅ done | **Allianz** | careers.allianz.com | Phenom (sitemap + JSON-LD mode) | 4 German ML/AI roles |
| ✅ done | **Bayer** | jobs.bayer.com | Phenom (Google-for-Jobs RSS mode) | 4 German ML/AI roles |
| ✅ done | **Merck KGaA** | careers.merckgroup.com | Phenom (sitemap + JSON-LD) | 1 German ML/AI role |
| ✅ done | **Procter & Gamble** | www.pgcareers.com | Phenom (sitemap + JSON-LD) | 1 German ML/AI role |
| ✅ done | **Thermo Fisher Scientific** | jobs.thermofisher.com | Phenom (sitemap + JSON-LD) | 0 currently, wired |
| ✅ done | **PwC Germany** | jobs.pwc.de | Phenom (urlset + JSON-LD) | 0 currently, wired |
| skip | **Microsoft** | jobs.careers.microsoft.com | Eightfold AI (not Phenom) | Different platform; would need new scraper |
| todo | **Mercedes-Benz Group** | group.mercedes-benz.com/careers | own / SF | Stuttgart, ML / autonomous driving |
| todo | **Munich Re** | munichre.com/en/career | likely Workday (private tenant) | Reinsurance ML |
| todo | **Lufthansa Group** | lufthansagroup.careers | SAP SF / own | Operations ML |
| todo | **adidas** | careers.adidas-group.com | Workday (probe failed earlier - re-investigate) | Retail ML, Herzogenaurach |
| todo | **Deutsche Telekom** | careers.telekom.com | Avature likely | T-Labs / AI |
| todo | **Schaeffler** | jobs.schaeffler.com | own / Phenom | Automotive components ML |
| todo | **Otto Group** | jobs.otto.de / ottogroup.com | own / SF | E-comm ML, Hamburg |
| todo | **Hensoldt** | hensoldt.wd3.myworkdayjobs.com | Workday (422 on probes - needs session/CSRF) | Defense AI |
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
- **Jobs2Web / SF HTML** (BMW pattern) - one-off HTML parsers per tenant, like
  BMW. Workable, just bespoke.
- **Avature** - server-rendered HTML; per-tenant parser needed.
- **Workday private tenants** (e.g. Hensoldt) - CXS endpoint exists but rejects
  bodies without CSRF; would need a session-bootstrap step.
