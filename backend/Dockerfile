# Backend image for QShield Twin.
#
# Build context is the repository root (see docker-compose.yml) so that
# pyproject.toml, uv.lock and the backend package are all available.
#
#   docker build -f backend/Dockerfile -t qshield-backend .
#
# Dependencies are installed reproducibly from uv.lock with `uv sync --frozen`.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install uv (used to resolve/install from the checked-in lockfile).
RUN pip install --no-cache-dir uv

# Install runtime dependencies first (better layer caching).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Application code.
COPY backend ./backend

# Run as an unprivileged user. `/data` is the mount point for the SQLite
# volume declared in docker-compose.yml; it must be writable by appuser so a
# freshly created named volume is usable without root.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown -R appuser /app /data
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').status==200 else 1)"

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
