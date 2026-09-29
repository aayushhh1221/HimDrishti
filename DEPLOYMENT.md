# HimDrishti — Deployment Guide
## SIH 2026 · PS 26059

> **Prototype notice:** HimDrishti is an SIH 2026 prototype. Not for operational use.

---

## Architecture

```
GitHub Repository (https://github.com/your-org/HimDrishti)
        │
        ├── Render Web Service  →  FastAPI backend (himdrishti-api)
        │       PORT              $PORT (injected by Render)
        │       Start             uvicorn backend.main:app --host 0.0.0.0 --port $PORT
        │       Health            GET /health
        │
        └── Render Static Site  →  React/Vite frontend (himdrishti-ui)
                Build             npm ci && npm run build (inside frontend/)
                Publish           frontend/dist/
                SPA fallback      /* → /index.html
```

---

## Environment Variables

### Backend (himdrishti-api)

| Variable | Description | Example value |
|---|---|---|
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `https://himdrishti-ui.onrender.com` |
| `PORT` | TCP port (injected by Render automatically) | (do not set manually) |

### Frontend (himdrishti-ui)

| Variable | Description | Example value |
|---|---|---|
| `VITE_API_BASE_URL` | Deployed backend base URL | `https://himdrishti-api.onrender.com` |

> **Order of operations:** Deploy the backend first → get its public URL → set `VITE_API_BASE_URL` → deploy/redeploy the frontend.

---

## Render Setup Steps

### 1. Deploy Backend (himdrishti-api)

1. Connect your GitHub repository to Render.
2. Create a **Web Service**:
   - **Runtime:** Python 3.11
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Health check path:** `/health`
3. In **Environment Variables**, add:
   - `ALLOWED_ORIGINS` = *(leave empty for now; fill after frontend URL is known)*
4. Deploy. Note the public URL: `https://himdrishti-api.onrender.com` (example).

### 2. Deploy Frontend (himdrishti-ui)

1. Create a **Static Site**:
   - **Root directory:** `frontend`
   - **Build command:** `npm ci && npm run build`
   - **Publish directory:** `dist`
2. In **Environment Variables**, add:
   - `VITE_API_BASE_URL` = `https://himdrishti-api.onrender.com`
3. Add **Redirect/Rewrite rule**:
   - Source: `/*` → Destination: `/index.html` (for SPA routing)
4. Deploy. Note the public URL: `https://himdrishti-ui.onrender.com` (example).

### 3. Update CORS

After both are deployed:
1. Go back to **himdrishti-api** → Environment Variables.
2. Set `ALLOWED_ORIGINS` = `https://himdrishti-ui.onrender.com`.
3. Trigger a **Manual Redeploy** of the backend.

---

## Local Development

### Backend

```bash
# From project root
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
# From frontend/
npm install
npm run dev
```

Frontend auto-proxies `/api/*` to `http://localhost:8000` (see `vite.config.ts`).

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/api/v1/routes/generate` | Route generation |
| GET | `/api/v1/risk/{route_id}` | Risk profile |
| GET | `/api/v1/forecast` | Forecast metadata |
| GET | `/api/v1/provenance` | Data provenance |
| GET | `/api/v1/alerts` | Operational alerts |
| POST | `/api/v1/replay/run` | Historical replay |
| POST | `/api/v1/planning/departure-windows` | Departure window planning |
| GET | `/docs` | OpenAPI / Swagger UI |

---

## Render Free-Tier Limitations

- **Cold start:** Free-tier backend spins down after 15 minutes of inactivity. The first request after a cold start may take 30–60 seconds while the service restarts. The frontend displays a professional "unavailable" state and a retry option during this period.
- **Compute:** Free tier has limited CPU/RAM. `POST /api/v1/routes/generate` (120s timeout) and `POST /api/v1/planning/departure-windows` (300s timeout) may be slower on free tier.
- **Disk:** No persistent disk on free tier. Historical replay data is bundled in `data/historical_replay/` within the repository.

---

## Security Notes

- No secrets committed to source code.
- CORS explicitly lists allowed origins — no wildcard `*` in production.
- Debug mode disabled in production (uvicorn standard mode, not `--reload`).
- Stack traces not exposed through normal API error responses.
- `.env` files are in `.gitignore`.

---

## No Secrets Policy

The following must NEVER be committed to the repository:
- `.env`, `.env.local`, `.env.production`
- API keys, access tokens, passwords
- Render deploy hook URLs
- Database connection strings

---

*SIH 2026 · PS 26059 · Prototype — not for operational use*
