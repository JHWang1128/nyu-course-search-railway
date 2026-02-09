# Local Development Guide

## Prerequisites

- **Python 3.11+** (with `uv` package manager recommended)
- **PostgreSQL 14+** with `pgvector` extension
- **Redis** (optional, for caching)

## Quick Start

### 1. Clone & Setup Environment

```bash
git clone <repo-url>
cd nyu-course-search

# Using uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Or using pip
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Start PostgreSQL (if not running)
brew services start postgresql@15  # macOS

# Create database
createdb nyucourses

# Enable pgvector extension
psql nyucourses -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 3. Environment Variables

Create a `.env` file or export these variables:

```bash
export DATABASE_URL="postgresql://localhost:5432/nyucourses"
export SECRET_KEY="your-dev-secret-key"
export ADMIN_EMAILS="your-email@nyu.edu"
# Optional:
export RESEND_API_KEY="re_xxx"  # For email OTP (leave empty for DEV mode)
export REDIS_URL="redis://localhost:6379"
```

### 4. Run the Application

```bash
# Development mode with auto-reload
uv run uvicorn app.main:app --reload --port 8000

# Or without uv
uvicorn app.main:app --reload --port 8000
```

Visit: http://localhost:8000

### 5. Initial Data Setup

1. **Scrape Courses**: 
   ```bash
   curl -X POST http://localhost:8000/admin/scrape
   ```
   This populates ~17,000 courses from the NYU bulletin.

2. **Generate Embeddings**: 
   ```bash
   uv run python -m scripts.generate_embeddings
   ```
   This takes ~30-60 minutes for all courses.

3. **Create Vector Index** (for fast search):
   ```bash
   psql nyucourses -c "CREATE INDEX courses_embedding_idx ON courses USING hnsw (embedding vector_cosine_ops);"
   ```

## Features

| Feature | Description |
|---------|-------------|
| **Semantic Search** | Natural language course search using Nomic embeddings |
| **Live Classes** | Real-time class schedule from bulletins.nyu.edu API |
| **Save/Upvote** | Bookmark and upvote courses (requires login) |
| **Authentication** | Email OTP for @nyu.edu addresses |

## Development Notes

### DEV MODE (No Resend API Key)

When `RESEND_API_KEY` is not set:
- OTP codes are printed to the terminal instead of being emailed
- Check your terminal output for login codes

### Database Inspection

```bash
psql nyucourses -c "\dt"                              # List tables
psql nyucourses -c "SELECT COUNT(*) FROM courses;"    # Count courses
psql nyucourses -c "SELECT COUNT(*) FROM courses WHERE embedding IS NOT NULL;"  # Embedded
```

### Running Tests

```bash
uv run pytest
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `pgvector` not found | Run `CREATE EXTENSION vector;` in psql |
| Port 8000 in use | Use `--port 8001` flag |
| First search slow (~7s) | Embedding model loading; subsequent searches are fast |
| Vector search slow | Ensure HNSW index exists (see step 5.3) |
