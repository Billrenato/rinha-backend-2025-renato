# Dockerfile
FROM python:3.11-slim

# Instalar dependências base
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copiar requirements (iremos instalar httpx, fastapi, uvicorn)
COPY ./app /app/app
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

# cria diretório para DB (permitir persistência quando usar volume)
RUN mkdir -p /data

ENV PYTHONUNBUFFERED=1
ENV PORT=9999

# Comando default (usamos uvicorn)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9999", "--workers", "1"]
