# Build stage
FROM python:3.11-slim as builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install poetry and configure it with debug logging
ENV PATH=$PATH:/root/.local/bin
ENV PIP_VERBOSE=1
ENV POETRY_VERBOSE=1
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    poetry config virtualenvs.in-project true && \
    poetry config --list

# Copy only the files needed for installation
COPY pyproject.toml poetry.lock README.md ./
COPY etc ./etc
COPY mmdb_server ./mmdb_server

# Install dependencies with verbose output
RUN poetry install -vvv --no-interaction --no-ansi --no-cache

# Runtime stage
FROM gcr.io/distroless/python3:nonroot
LABEL authors="Erik Andri Budiman, Steve Clement"
LABEL optimized-by="Gordon"
LABEL forked-by="2snem6"
WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /app/.venv/lib/python3.11/site-packages /app/packages
COPY --from=builder /app/mmdb_server ./mmdb_server
COPY --from=builder /app/etc/server.conf.sample ./etc/server.conf
COPY db/country.json ./db/country.json

ENV PYTHONPATH=/app/packages

# Create volume mount point
VOLUME /app/db

ENTRYPOINT ["python3", "mmdb_server/mmdb_server.py"]
