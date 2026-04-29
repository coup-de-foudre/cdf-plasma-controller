FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

LABEL maintainer="Mike McCoy <michael.b.mccoy@gmail.com>"

WORKDIR /app

COPY pyproject.toml uv.lock* ./
COPY vendor /app/vendor
COPY plasma /app/plasma
COPY tests /app/tests
COPY plasma_controller.py osc_runner.py ./

RUN uv sync --frozen --no-dev || uv sync --no-dev
