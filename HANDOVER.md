# Handover

Date: 7 October 2026 (Africa/Johannesburg)

## Ownership and Git

- Owner: `MrMoneyDeveloper`.
- Working repository: `https://github.com/MrMoneyDeveloper/AI-Site-Factory-and-Outreach-Pipeline` (public).
- Default working branch: `main`.
- `origin` is the owned copy; `upstream` retains the BusiM5 source repository.
- Source history starts this handover at `3d695c4`. Its remote was pulled with `--ff-only` and was already current.
- All inherited commit history and contributor attribution are preserved. No license was added; the source had no license file.

## Repairs in this handover

The inherited merge commit contained literal conflict markers in `backend/main.py`, `frontend/src/App.js`, and `frontend/src/App.css`, preventing execution. Resolution retains the current industry scrape/review/Netlify workflow from `6ee84e1`; the resolved frontend files match that pre-merge version. The conflicting old manual-intake UI and demo URL scraper were not combined into the current workflow. Legacy lead-cleaning and content-generation API routes remain available.

The obsolete Create React App example test was replaced with three meaningful UI checks. Six backend regression tests cover API startup/presets, validation, mocked scraping, cleaning/content generation, and escaped HTML ZIP output. Tracked Python bytecode was removed from the index. Root and frontend documentation now describe implemented behavior.

## Verification record

- Backend: 6 unittest tests passed using FastAPI TestClient.
- Frontend: 3 Jest/React Testing Library tests passed.
- Production frontend build: compiled successfully.
- `git diff --check`: passed.
- Python 3.13.7; Node.js 24.15.0; npm 11.12.1.
- Build warnings: outdated Browserslist data and a Node `fs.F_OK` deprecation from tooling.
- Live Apify runs, Netlify publication, hosted service ownership, and provider credentials were not validated. Automated tests do not make live provider calls.

## Taking over locally

1. Follow the root README to install dependencies and configure ignored environment files.
2. Use your own Apify and Netlify accounts. Keep tokens server-side.
3. Start both services; inspect `/docs` and confirm the frontend loads presets.
4. When ready to spend provider credits, perform one small scrape and one selected-business deployment. Inspect the published page and save its URLs.
5. Check Netlify manually for processing/failed uploads and remove unwanted sites in that account.
6. Run the documented offline checks before committing future changes.

## Known limitations and next work

| Priority | Issue | Next step |
| --- | --- | --- |
| Before public hosting | No authentication or rate limiting on paid provider routes | Add access control and usage limits; CORS is not authentication |
| High | Provider network exceptions can escape as generic server errors | Handle requests timeouts/connection failures with structured responses |
| High | Netlify `error` states currently map to `processing` | Return a failed result with actionable details; add mocked deployment lifecycle coverage |
| High | Sequential synchronous provider calls can exceed host request deadlines | Move long-running scrape/deploy work to jobs with status tracking |
| High | Repeated deployment creates new sites; failed uploads can leave empty sites | Add idempotency, persisted site IDs, and cleanup handling |
| Medium | No database; UI state disappears on refresh | Persist leads, deployment URLs, and job results |
| Medium | Generation is deterministic template output | Integrate an actual model with reviewable output if required |
| Medium | No CRM, email, or outreach implementation | Define the intended workflow before adding integrations |
| Medium | UI says 10 results regardless of backend setting | Render the configured limit throughout the UI |
| Medium | Token presence treats placeholders as configured | Validate configuration and improve provider diagnostics |
| Medium | Frontend origins are hardcoded and root dotenv overrides process values | Make deployment configuration explicit before switching hosts |
| Maintenance | Older Create React App tooling and stale browser metadata | Review tooling/dependency updates in a separate tested change |

Generated landing pages include their generation context and use an external Unsplash background image. Review those choices before customer delivery. Existing hosted URLs mentioned in earlier documentation were not transferred or verified for this repository.

## Future synchronization

```powershell
git pull --ff-only origin main
# Make and verify changes, then commit them.
git push origin main
```

To review source updates, fetch `upstream` and inspect the diff on a separate branch. Do not automatically merge the inherited broken merge into repaired code. No hosting deployment or ongoing sync automation was created during this handover.
