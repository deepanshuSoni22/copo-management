# Environment Setup Guide

## The Problem Fixed

The application was configured to read critical settings from environment variables (for production on Render), but these weren't set in the local development environment, causing crashes.

## Changes Made

### 1. **settings.py** - Added Development Fallbacks

**SECRET_KEY**: 
- **Production**: Uses `SECRET_KEY` environment variable (required on Render)
- **Development**: Falls back to a default dev key if not set

**DEBUG Mode**:
- **Production**: Uses `DEBUG` environment variable (should be `False`)
- **Development**: Defaults to `True` if not set

**Database**:
- **Production**: Uses `DATABASE_URL` for PostgreSQL on Render
- **Development**: Falls back to SQLite (`db.sqlite3`) if `DATABASE_URL` not set

### 2. **.env.example** - Documentation Template

Created a template file showing which environment variables are needed for production.

## Local Development Setup

### Option 1: No Configuration Needed (Recommended for Local Dev)
Simply run the app - it will automatically use:
- Default development SECRET_KEY
- DEBUG=True
- SQLite database
- ALLOWED_HOSTS=127.0.0.1

```bash
# Activate virtual environment
venv\Scripts\activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver
```

### Option 2: Use Environment Variables (Optional)
If you want to test with environment variables locally:

1. Create a `.env` file (copy from `.env.example`):
```bash
copy .env.example .env
```

2. Edit `.env` and set your values:
```
SECRET_KEY=your-generated-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=sqlite:///db.sqlite3
```

3. Install `python-dotenv`:
```bash
pip install python-dotenv
```

4. Update `settings.py` to load `.env` (add at the top):
```python
from dotenv import load_dotenv
load_dotenv()
```

## Production Setup (Render)

### Environment Variables to Set in Render Dashboard:

1. **SECRET_KEY** (Required):
   ```bash
   # Generate a secure key:
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
   Copy the output and set it as `SECRET_KEY` in Render.

2. **DEBUG** (Required):
   ```
   DEBUG=False
   ```

3. **ALLOWED_HOSTS** (Required):
   ```
   ALLOWED_HOSTS=your-app-name.onrender.com
   ```
   (Replace with your actual Render domain)

4. **DATABASE_URL** (Auto-set by Render):
   Render automatically provides this when you add a PostgreSQL database.

### Render Configuration Files

The repository includes `render.yaml` which should handle the deployment automatically. Make sure:

- Build Command: `./build.sh`
- Start Command: `gunicorn copo_management_system.wsgi:application`

## Database Management

### Local (SQLite)
- Database file: `db.sqlite3` (created automatically)
- No setup needed - just run migrations

### Production (PostgreSQL on Render)
- Automatically configured via `DATABASE_URL`
- Migrations run during deployment (in `build.sh`)

## Troubleshooting

### Error: "SECRET_KEY setting must not be empty"
**Cause**: Environment variable not set
**Solution**: 
- **Local dev**: The fix in this PR handles it automatically
- **Production**: Set `SECRET_KEY` in Render dashboard

### Error: "No module named 'dj_database_url'"
**Cause**: Dependencies not installed
**Solution**: 
```bash
pip install -r requirements.txt
```

### Error: "No DATABASE_URL environment variable set"
**Cause**: This is just a warning (not an error)
**Impact**: App falls back to SQLite for local development
**Solution**: Ignore this warning in local dev, or set `DATABASE_URL` if you want to use PostgreSQL locally

## Best Practices

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Generate new SECRET_KEY for production** - Don't use the default dev key
3. **Keep DEBUG=False in production** - Always set this in Render
4. **Use SQLite for local dev** - Easier setup, no PostgreSQL installation needed
5. **Test with DEBUG=False locally** before deploying - Catches static file issues

## Quick Reference

| Setting | Local Dev (Default) | Production (Render) |
|---------|-------------------|---------------------|
| SECRET_KEY | Auto-generated dev key | Set in Render dashboard |
| DEBUG | True | False |
| DATABASE | SQLite (db.sqlite3) | PostgreSQL (via DATABASE_URL) |
| ALLOWED_HOSTS | 127.0.0.1 | your-app.onrender.com |

## Next Steps

After this fix:
1. ✅ Server starts without errors locally
2. ✅ No environment setup needed for local development
3. ✅ Production deployment on Render will work with proper env vars set
4. Test the application functionality
5. Set production environment variables in Render dashboard
6. Deploy to production
