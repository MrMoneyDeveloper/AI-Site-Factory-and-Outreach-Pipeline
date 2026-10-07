# Frontend

React 19 interface for choosing Apify industry presets, reviewing business leads, and submitting selected leads for Netlify deployment through the FastAPI backend.

See the [root README](../README.md) for complete setup and the [handover](../HANDOVER.md) for remaining work.

From this directory:

```powershell
npm.cmd ci
npm.cmd start
npm.cmd test -- --watchAll=false --runInBand
npm.cmd run build
```

Copy `.env.example` to `.env` on first setup. `REACT_APP_API_BASE_URL` points to the backend and defaults to `http://127.0.0.1:8000`. Restart the development server or rebuild after changing it. Never put provider tokens in frontend environment variables.

Production output is `build/`. The app uses Create React App (`react-scripts`) and ordinary CSS. Lead/deployment state is held in memory and resets on refresh. Tests mock HTTP requests so they do not scrape or publish sites.
