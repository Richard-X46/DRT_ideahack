# FastAPI Migration Branch

This branch contains the FastAPI version of the DRT IdeaHack application.

## Key Changes from Flask to FastAPI

### 1. **Simplified Subpath Mounting**
**Flask (complex):**
```python
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.middleware.proxy_fix import ProxyFix

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
application = DispatcherMiddleware(simple_app, {'/drt-ideahack': app})
```

**FastAPI (simple):**
```python
app = FastAPI(root_path="/drt-ideahack")
```

### 2. **Async by Default**
- All external API calls now use `httpx.AsyncClient` instead of `requests`
- Multiple API calls can run concurrently (vehicle positions + static routes)
- Better performance under load

### 3. **Modern Dependency Management**
- Removed: `flask`, `gunicorn`, `requests`
- Added: `httpx`, `python-multipart`, `uvicorn[standard]`
- Kept: All other dependencies (folium, geopy, etc.)

### 4. **Server Changes**
- **Old:** Gunicorn (WSGI server)
- **New:** Uvicorn (ASGI server)
- Better async support and performance

### 5. **Template System**
- FastAPI uses Jinja2 directly (same as Flask)
- Minor syntax change: `url_for('static', path='...')` instead of `url_for('static', filename='...')`

## Running Locally

```bash
# Install dependencies
uv pip install -e .

# Run with uvicorn
uvicorn src.app.main_fastapi:app --reload --port 5000

# Or run the script directly
python src/app/main_fastapi.py
```

## Docker Deployment

Same as before, but now uses Uvicorn:

```yaml
drt-ideahack:
    image: ghcr.io/richard-x46/drt-ideahack:latest
    container_name: drt-ideahack
    env_file:
      - .env
    ports:
      - "5000:5000"
    depends_on:
      - postgres
    environment:
      FLASK_ENV: production
      PYTHONPATH: /app
      PYTHONUNBUFFERED: 1
    mem_limit: 2000M
    mem_reservation: 200M
```

## Caddy Configuration

**No changes needed!** The same Caddy config works:

```caddyfile
richard-x46.me, www.richard-x46.me {

    handle /drt-ideahack* {
        reverse_proxy 127.0.0.1:5000
    }

    handle / {
        root * /home/ec2-user/docks/static
        file_server
    }
}
```

## Benefits of FastAPI Version

1. ✅ **Simpler subpath mounting** - one line vs. complex middleware
2. ✅ **Better performance** - async I/O for API calls
3. ✅ **Automatic API docs** - visit `/drt-ideahack/docs` for interactive API documentation
4. ✅ **Type safety** - better error catching during development
5. ✅ **Modern Python** - uses async/await patterns
6. ✅ **Less boilerplate** - cleaner, more maintainable code

## Testing the Migration

1. Build and run the Docker container
2. Visit `https://richard-x46.me/drt-ideahack/`
3. Test address search and map generation
4. Check `/drt-ideahack/docs` for auto-generated API documentation

## Performance Comparison

**Flask:**
- Sequential API calls (vehicle positions, then routes)
- WSGI (synchronous)
- ~3-5 seconds per map generation

**FastAPI:**
- Concurrent API calls (vehicle positions + routes simultaneously)
- ASGI (asynchronous)
- ~1-2 seconds per map generation (estimated)

## Migration Checklist

- [x] Create FastAPI main app
- [x] Convert all routes to async
- [x] Replace `requests` with `httpx` (async)
- [x] Update templates for FastAPI's `url_for` syntax
- [x] Update Dockerfile to use Uvicorn
- [x] Update dependencies in pyproject.toml
- [ ] Update templates to use `second_page_fastapi.html` naming
- [ ] Test all routes
- [ ] Test address suggestions
- [ ] Test map generation
- [ ] Verify static files load correctly
- [ ] Test behind Caddy reverse proxy
- [ ] Performance benchmarking

## Next Steps

1. Test this branch locally
2. Deploy to staging/test environment
3. Compare performance with Flask version
4. If successful, merge to main
