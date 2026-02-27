# PETER - container image
# Goal: reproducible deployment across providers.

FROM python:3.13-slim

# System deps: poppler tools for pdftotext/pdftoppm/pdfinfo
RUN apt-get update \
  && apt-get install -y --no-install-recommends poppler-utils \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source
COPY pyproject.toml README.md /app/
COPY src /app/src

# Install in editable-ish mode without venv (container is isolated)
RUN pip install --no-cache-dir -e .

ENV PETER_DATA_DIR=/app/data

# Default: show help
ENTRYPOINT ["peter"]
CMD ["--help"]
