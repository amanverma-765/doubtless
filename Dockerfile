FROM python:3.14-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg gcc libc6-dev \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 HOME=/cache

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Create application user and group (UID 1000) with home directory at /cache
RUN groupadd -g 1000 doubtless \
 && useradd -u 1000 -g doubtless -d /cache -s /bin/bash doubtless \
 && mkdir -p /cache /app/data \
 && chown -R doubtless:doubtless /cache /app/data

RUN echo "/app/.venv/lib/python3.14/site-packages/nvidia/cublas/lib" > /etc/ld.so.conf.d/nvidia.conf \
 && echo "/app/.venv/lib/python3.14/site-packages/nvidia/cudnn/lib" >> /etc/ld.so.conf.d/nvidia.conf \
 && echo "/app/.venv/lib/python3.14/site-packages/nvidia/cuda_nvrtc/lib" >> /etc/ld.so.conf.d/nvidia.conf \
 && ldconfig

ENV LD_LIBRARY_PATH="/app/.venv/lib/python3.14/site-packages/nvidia/cublas/lib:/app/.venv/lib/python3.14/site-packages/nvidia/cudnn/lib:/app/.venv/lib/python3.14/site-packages/nvidia/cuda_nvrtc/lib:${LD_LIBRARY_PATH}"

# Default entrypoint runs doubtless CLI (defaults to api server)
CMD ["/app/.venv/bin/doubtless", "api"]
