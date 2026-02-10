# Remote Deployment (Railway)

## Prerequisites

- Railway Account (https://railway.app)
- GitHub Repository linked to Railway
- Resend Account (https://resend.com) for email OTP

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
| `ADMIN_EMAILS` | `your-email@nyu.edu` (comma-separated for multiple) |
| `RESEND_API_KEY` | Your Resend API key (required for email login) |

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

Takes 30-60 minutes for all courses.

### Step 3: Upload Local Database (Recommended)

Instead of scraping and generating embeddings on Railway, dump your local DB and restore:

```bash
# Dump local database
pg_dump -Fc nyucourses > nyucourses.dump

# Restore to Railway (get URL from Railway → PostgreSQL → Variables)
pg_restore --no-owner --no-acl -d "YOUR_RAILWAY_DATABASE_URL" nyucourses.dump
```

### Step 4: Create Vector Index

The HNSW index requires too much shared memory for Railway's free tier. Use IVFFlat instead:

```bash
psql "YOUR_RAILWAY_DATABASE_URL" \
  -c "CREATE INDEX courses_embedding_idx ON courses USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
```

## Features

| Feature | Description |
|---------|-------------|
| **Semantic Search** | Natural language course search using Nomic embeddings + pgvector |
| **Live Classes** | Real-time class schedules from bulletins.nyu.edu API |
| **Authentication** | Email OTP via Resend, restricted to `@nyu.edu` |
| **Save/Upvote** | Bookmark and upvote courses (requires login) |
| **My Courses** | Personal page showing saved and upvoted courses |
| **Admin Panel** | Stats, user management, scraper control (admin-only) |

## User Roles

| Role | Access |
|------|--------|
| **Guest** | Search courses, view details, view live classes |
| **Logged-in User** | Save/upvote courses, My Courses page |
| **Admin** | Admin panel (stats, users, settings, scraper) |

Admin access is granted to emails listed in `ADMIN_EMAILS`.

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection (auto-set by Railway) |
| `SECRET_KEY` | Yes | JWT signing key (32+ chars) |
| `ADMIN_EMAILS` | Yes | Comma-separated admin emails |
| `RESEND_API_KEY` | Yes | Resend API key for email OTP |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `pgvector` error | Run `CREATE EXTENSION vector;` in Railway PostgreSQL console |
| Database not connecting | Check `DATABASE_URL` format (`postgres://` → `postgresql://`) |
| First search slow (~7s) | Embedding model loads on first request; subsequent searches are fast |
| HNSW index fails | Use IVFFlat index instead (see Step 4) — Railway free tier has limited shared memory |
| Search results slow | Ensure HNSW index is created (see Step 3) |
| OTP not received | Verify `RESEND_API_KEY` and sender domain in Resend dashboard |
| Admin page redirects | Ensure your email is in `ADMIN_EMAILS` and you're logged in |

## Monitoring

```
GET https://your-app.railway.app/admin/stats
```

Returns:
```json
{
  "total_courses": 17122,
  "total_users": 0,
  "courses_with_embeddings": 17122
}
```
