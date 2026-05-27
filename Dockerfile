FROM python:3.13-slim

RUN useradd -m appuser

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir --upgrade pip

# Install dependencies manually
RUN pip install --no-cache-dir \
    aiosqlite \
    alembic \
    asyncpg \
    bcrypt \
    fastapi \
    httpx \
    Pillow \
    prometheus-fastapi-instrumentator \
    pydantic-settings \
    "pydantic[email]" \
    pyjwt \
    pyotp \
    pytest \
    pytest-asyncio \
    qrcode \
    "redis[asyncio]" \
    "sqlalchemy[asyncio]" \
    starlette \
    "uvicorn[standard]"

RUN rm -rf /app/.venv

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]