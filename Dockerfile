FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.7.19 /uv /bin/uv

ENV PATH="/bin:$PATH"

ENV UV_VENV=disabled
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock requirements-prod.txt ./

# Use Docker Buildkit cache mounts if available (optional)
RUN --mount=type=cache,target=/root/.cache/uv uv pip sync --system --break-system-packages requirements-prod.txt

# RUN pip install gunicorn

COPY . .

EXPOSE 80

CMD ["gunicorn", "core.wsgi:application", "-b", "0.0.0.0:80", "--workers=3", "--timeout=60"]

