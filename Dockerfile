FROM python:3.11-slim

# Create a non-root user for improved security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build/runtime deps (cache python packages between layers)
RUN apt-get update && apt-get install -y --no-install-recommends \
	build-essential \
	libpq-dev \
	gcc \
	&& rm -rf /var/lib/apt/lists/*

# Install Python packages — copy only requirements first to leverage cache
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app code and set proper ownership
COPY . /app
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

CMD ["python", "bot.py"]
