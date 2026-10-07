# AI Site Factory and Outreach Pipeline

A React and FastAPI prototype for finding local businesses through Apify, reviewing leads, and generating static landing pages for deployment to Netlify.

## Repository and provenance

Owned copy: [MrMoneyDeveloper/AI-Site-Factory-and-Outreach-Pipeline](https://github.com/MrMoneyDeveloper/AI-Site-Factory-and-Outreach-Pipeline).

This copy preserves the Git history from [BusiM5/AI-Site-Factory-Fork](https://github.com/BusiM5/AI-Site-Factory-Fork), originally forked from [DeveloperRSA/AI-Site-Factory-and-Outreach-Pipeline](https://github.com/DeveloperRSA/AI-Site-Factory-and-Outreach-Pipeline). The former remote name redirects to the BusiM5 repository. Original contributor attribution remains in the history. No license file was present at handover; this copy does not add a license or claim authorship of inherited work.

## What works in the code

- Eight industry presets: plumbers, electricians, HVAC, roofing, landscaping, dentists, restaurants, and mechanics.
- Apify Google Maps scraping by location; the default limit is 10 businesses per industry.
- Lead selection and review in the browser.
- Deterministic HTML generation, ZIP packaging, and Netlify site creation/upload.
- Legacy API endpoints for cleaning a lead and generating a template content packet.

Generation is currently template-based. An AI model, database, CRM integration, email delivery, and outreach automation are not implemented. Browser state is lost on refresh. Live provider credentials and account access are required for scraping/deployment.

## Project layout

| Path | Purpose |
| --- | --- |
| `backend/main.py` | FastAPI routes, presets, normalization, HTML generation, provider calls |
| `backend/requirements.txt` | Pinned Python dependencies |
| `backend/test_main.py` | Offline backend regression tests |
| `frontend/src/App.js` | Scrape, review, and deploy interface |
| `frontend/src/App.css` | Interface styles |
| `frontend/src/App.test.js` | Mocked frontend checks |
| `.env.example` | Server configuration template |
| `frontend/.env.example` | Browser API URL template |
| `package.json` | Combined local development commands |
| `HANDOVER.md` | Maintenance notes, verification, and next steps |

## Local setup

Use Python 3.10+ and Node.js with npm. The October 2026 handover was checked with Python 3.13.7, Node 24.15.0, and npm 11.12.1.

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env
npm.cmd ci
python -m pip install -r backend/requirements.txt
npm.cmd ci --prefix frontend
npm.cmd run dev
```

Copy the environment templates only on first setup; preserve existing credentials. Edit the root `.env` with your own provider tokens. If PowerShell blocks virtual-environment activation, use `.\.venv\Scripts\python.exe` directly for Python commands and start the frontend in another terminal.

- Frontend: <http://localhost:3000>
- Backend health: <http://127.0.0.1:8000/>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

Separate terminals can run `npm.cmd run backend` and `npm.cmd run frontend`. `npm.cmd run pipeline` is the convenience alternative: its pre-step installs root, backend, and frontend dependencies before starting both servers. Use `npm.cmd run dev` for subsequent runs without reinstalling.

## Configuration

| Variable | Location | Meaning |
| --- | --- | --- |
| `APIFY_API_TOKEN` | Root `.env` | Required for live scraping |
| `NETLIFY_API_TOKEN` | Root `.env` | Required to create and deploy sites |
| `APIFY_ACTOR_ID` | Root `.env` | Defaults to `compass~crawler-google-places` |
| `DEFAULT_LOCATION_QUERY` | Root `.env` | Defaults to `Durban, South Africa` |
| `SCRAPE_RESULT_LIMIT` | Root `.env` | Integer limit per industry; default `10` |
| `REACT_APP_API_BASE_URL` | `frontend/.env` | Defaults to `http://127.0.0.1:8000` |

Restart the backend after server configuration changes. Restart/rebuild the frontend after API URL changes. The UI currently displays a hardcoded limit of 10 even if the backend limit changes. Configuration status checks token presence, not validity; template placeholder values also count as present.

The root `.env` is loaded with `override=True`, so it takes precedence over process variables. Keep secrets out of `REACT_APP_*` variables: those are bundled into browser code. Environment files, virtual environments, dependencies, and build output are ignored by Git.

## Workflow

1. Start both services and configure provider tokens.
2. Select industry presets and a target location. All presets are selected initially.
3. Run the scrape; review returned businesses and any per-industry failures.
4. Adjust lead selection. Returned leads are selected initially.
5. Use **Deploy selected** to create real Netlify sites and upload generated pages.
6. Save returned site URLs and check Netlify for deployments still processing.

Each deployment creates a new site; retries can create additional sites. Scraping and deployment may incur provider usage charges. The application does not automatically send outreach messages.

## API

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/` | Health response |
| GET | `/api/config/status` | Token presence and scrape settings |
| GET | `/api/industries` | Industry presets and actor input templates |
| POST | `/api/scrape` | Accepts `industryIds` and optional `locationQuery` |
| POST | `/api/deploy` | Accepts `leads` returned by scraping |
| POST | `/api/leads/clean` | Normalizes a manually supplied lead |
| POST | `/api/content/generate` | Returns template content for a cleaned lead |

See `/docs` for complete request and response schemas. The obsolete demo `/api/scrape/lead` route is not part of the current workflow.

## Verification

Run from the root:

```powershell
python -m unittest discover -s backend -p 'test_*.py' -v
npm.cmd test --prefix frontend -- --watchAll=false --runInBand
npm.cmd run build --prefix frontend
git diff --check
```

Backend tests use the installed FastAPI/Starlette TestClient and require `httpx`; install it with `python -m pip install httpx` if missing. Tests mock provider calls and do not need real tokens. A passing build does not verify Apify or Netlify account access.

## Hosting notes

The frontend builds into `frontend/build`. Set `REACT_APP_API_BASE_URL` to your backend URL before building. A backend host can install `backend/requirements.txt` and run `python -m uvicorn backend.main:app --host 0.0.0.0 --port <assigned-port>` from the repository root.

CORS origins are currently hardcoded in `backend/main.py`; add the actual frontend origin when changing hosts. No deployment automation is configured in this repository. Prior README hosting URLs are not verified as owned or operational for this copy.

The backend has no authentication, rate limits, or job queue. Before public use, protect the provider-backed routes and address the operational issues in the handover.

## Handover

Read [HANDOVER.md](HANDOVER.md) for the repair record, known limitations, ownership checklist, and recommended next work.

Your repository is `origin`; the source is retained as `upstream`. Normal synchronization:

```powershell
git pull --ff-only origin main
git push origin main
```

To inspect source updates without merging them:

```powershell
git fetch upstream
git log --oneline main..upstream/main
```

Review upstream changes on a separate branch before incorporating them, especially because the inherited main branch contained committed conflict markers.
