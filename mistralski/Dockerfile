FROM python:3.12-slim

WORKDIR /app

# Install Python deps (no gcc needed — all pure wheels)
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY config/ ./config/

RUN mkdir -p data

EXPOSE 80

CMD ["python", "scripts/play_web.py"]
