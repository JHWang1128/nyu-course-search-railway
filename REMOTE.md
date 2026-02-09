# Remote Deployment (Railway)

## Prerequisites

- Railway Account (https://railway.app)
- GitHub Repository linked to Railway

## Deployment Steps

### 1. Create Railway Project

1. Go to Railway Dashboard
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your `nyu-course-search` repository

### 2. Add PostgreSQL Database

1. In your Railway project, click **+ New** → **Database** → **PostgreSQL**
2. Railway automatically provides `DATABASE_URL` to your app

### 3. Enable pgvector Extension

After PostgreSQL is deployed:

1. Click on the PostgreSQL service
2. Go to **Query** tab
3. Run: 
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### 4. Set Environment Variables

In your app service settings, add:

| Variable | Value |
|----------|-------|
| `SECRET_KEY` | Generate with `openssl rand -hex 32` |
| `ADMIN_EMAILS` | `your-email@nyu.edu` |
| `RESEND_API_KEY` | Your Resend API key (for production emails) |

> Note: `DATABASE_URL` is automatically set by Railway PostgreSQL

### 5. Configure Build & Start

Railway auto-detects the `Procfile`. Ensure it contains:

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### 6. Deploy

Push to your GitHub main branch. Railway will auto-deploy.

## Post-Deployment Setup

### Step 1: Scrape Course Catalog

```bash
curl -X POST https://your-app.railway.app/admin/scrape
```

This will populate ~17,000 courses.

### Step 2: Generate Embeddings

Using Railway CLI:
```bash
railway run python -m scripts.generate_embeddings
```

Or via Railway shell (takes 30-60 minutes for all courses).

### Step 3: Create Vector Index

In Railway PostgreSQL Query tab:
```sql
CREATE INDEX courses_embedding_idx ON courses USING hnsw (embedding vector_cosine_ops);
```

This dramatically improves search speed (from ~3s to ~0.7s).

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection (auto-set by Railway) |
| `SECRET_KEY` | Yes | JWT signing key (32+ chars) |
| `ADMIN_EMAILS` | Yes | Comma-separated admin emails |
| `RESEND_API_KEY` | Prod | For email OTP. Without it, OTPs print to logs |

## Live Class Schedule

The app fetches live class data from `bulletins.nyu.edu`. This works automatically with no additional setup. Classes are fetched in real-time when viewing course details.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `pgvector` error | Run `CREATE EXTENSION vector;` in Railway PostgreSQL console |
| Database not connecting | Check `DATABASE_URL` format (Railway may use `postgres://`, app expects `postgresql://`) |
| First search slow (~7s) | Embedding model loads on first request; subsequent searches are fast |
| Search results slow | Ensure HNSW index is created (see Post-Deployment Step 3) |
| No live classes shown | Check if course code format matches NYU bulletin |

## Monitoring

Check app stats at:
```
https://your-app.railway.app/admin/stats
```

Returns:
```json
{
  "total_courses": 17122,
  "total_users": 0,
  "courses_with_embeddings": 17122
}
```
