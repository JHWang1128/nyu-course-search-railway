# NYU Course Search

AI-powered semantic search across 17,000+ NYU courses. Search in natural language, view live class schedules, and save your favorites.

## Features

- **🔍 Semantic Search** — Search courses using natural language (e.g., "machine learning for beginners")
- **📅 Live Class Schedules** — Real-time class sections from NYU bulletins API
- **🔖 Save & Upvote** — Bookmark and upvote courses you're interested in
- **📚 My Courses** — Personal page with your saved and upvoted courses
- **🔐 NYU Email Auth** — Secure login via email OTP (restricted to `@nyu.edu`)
- **⚙️ Admin Panel** — Stats, user management, and scraper controls

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python) |
| Database | PostgreSQL + pgvector |
| Embeddings | Nomic Embed Text v1.5 |
| Search | HNSW vector index (cosine similarity) |
| Frontend | Jinja2 + HTMX |
| Auth | Email OTP via Resend + JWT |
| Live Data | NYU Bulletins Class Search API |

## Quick Start

```bash
# Clone & setup
git clone https://github.com/kyunghyuncho/nyu-course-search.git
cd nyu-course-search

# Environment
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# Database
createdb nyucourses
psql nyucourses -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Configure (copy and edit with your values)
cp .env.example .env

# Run
source .env
uv run uvicorn app.main:app --reload --port 8000
```

Then populate data:
1. Scrape courses: `curl -X POST http://localhost:8000/admin/scrape`
2. Generate embeddings: `uv run python -m scripts.generate_embeddings`
3. Create search index:
   ```bash
   # Local (HNSW — faster, needs more memory)
   psql nyucourses -c "CREATE INDEX courses_embedding_idx ON courses USING hnsw (embedding vector_cosine_ops);"
   # Railway (IVFFlat — works on free tier)
   psql "YOUR_RAILWAY_URL" -c "CREATE INDEX courses_embedding_idx ON courses USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
   ```

For Railway deployment, you can dump your local DB and restore it directly — see [REMOTE.md](REMOTE.md).

See [LOCAL.md](LOCAL.md) for detailed local setup.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | JWT signing key |
| `ADMIN_EMAILS` | Yes | Comma-separated admin emails |
| `RESEND_API_KEY` | Yes | Resend API key for email OTP |

## License

MIT