FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Deps allegees pour Cloud Run (pas de perception camera)
COPY requirements-cloudrun.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Code serveur
COPY . /app/
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

RUN mkdir -p /app/static/documents /app/certs /app/data /app/data/certificates

# Cloud Run utilise la var PORT (defaut 8080)
EXPOSE 8080

ENTRYPOINT ["/app/docker-entrypoint.sh"]
