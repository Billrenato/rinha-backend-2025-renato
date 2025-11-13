# app/main.py
"""
Aplicação FastAPI para a Rinha de Backend 2025 - template didático.
Fornece:
 - POST /payments -> intermedia pagamento para um Payment Processor
 - GET  /payments-summary -> retorna resumo (default / fallback)
 
Estratégia implementada:
 - Health-check cacheado (TTL=4s) para evitar estourar limite 1 chamada /5s.
 - Escolha preferencial pelo processor "default" (menor taxa), mas
   considera 'failing' vindo do health-check.
 - Em caso de falha ao enviar para o escolhido, tenta fallback.
 - Registra resultados em SQLite (persistência simples).
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional
import uuid
import json
from app.db import init_db, record_payment, get_summary_db
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
import httpx
import os

from app.db import init_db, record_payment, get_summary_db
from app.utils import cached_health_check

app = FastAPI(title="Rinha Backend - Template FastAPI (estudo)")

# Endereços dos Payment Processors (quando em rede do docker-compose usar os nomes deles)
"""PAYMENT_PROCESSORS = {
    "default": os.getenv("PP_DEFAULT", "http://payment-processor-default:8080"),
    "fallback": os.getenv("PP_FALLBACK", "http://payment-processor-fallback:8080"),
}"""

PAYMENT_PROCESSORS = {
    "default": "http://localhost:8080",
    "fallback": "http://localhost:8081",
}


# Cada processor tem também uma "fee" conhecida localmente (no enunciado o default tem menor taxa).
# Para estudo definimos aqui fees fictícias — na Rinha real o fee vem do test runner (mas enunciado diz que
# o serviço default sempre terá a menor taxa). Ajuste conforme necessário.
PROCESSOR_FEES = {
    "default": 0.05,   # 5%
    "fallback": 0.07,  # 7%
}

# HTTP client timeout
HTTP_TIMEOUT = 3.0

# Inicializa banco (cria tabelas)
@app.on_event("startup")
async def startup():
    await init_db()

# -------------------------
# Schemas
# -------------------------
class PaymentIn(BaseModel):
    correlationId: uuid.UUID = Field(..., description="UUID único por requisição")
    amount: float = Field(..., gt=0, description="Valor do pagamento (decimal)")

class PaymentResponse(BaseModel):
    processor: str
    status_code: int
    message: Optional[str] = None

# -------------------------
# Lógica para escolher o processor
# -------------------------
async def decide_processor() -> Optional[str]:
    """
    Estratégia simples:
    - Checa health de ambos (cacheado para não ultrapassar limite de 1 chamada por 5s).
    - Se default não estiver failing -> escolhe default (menor taxa).
    - Se default failing e fallback ok -> fallback.
    - Se ambos failing -> retorna None (indisponível).
    Observação: health check retorna {"failing": bool, "minResponseTime": int}
    """
    # chama health checks paralelos (função cached_health_check trata caching e limites)
    default_hc_task = asyncio.create_task(cached_health_check("default", PAYMENT_PROCESSORS["default"]))
    fallback_hc_task = asyncio.create_task(cached_health_check("fallback", PAYMENT_PROCESSORS["fallback"]))
    default_hc, fallback_hc = await asyncio.gather(default_hc_task, fallback_hc_task)

    # Se default disponível priorizamos ele (menor taxa)
    if default_hc and not default_hc.get("failing", True):
        return "default"
    if fallback_hc and not fallback_hc.get("failing", True):
        return "fallback"
    return None

# -------------------------
# Endpoint POST /payments
# -------------------------
@app.post("/payments", response_model=PaymentResponse)
async def create_payment(payment: PaymentIn, request: Request):
    """
    Recebe o pagamento, decide processor e encaminha.
    Registra o resultado no banco (tabela payments).
    """
    # validação extra: correlationId único — aqui apenas logamos/registramos.
    chosen = await decide_processor()
    if not chosen:
        # Nenhum disponível agora
        raise HTTPException(status_code=503, detail="No payment processor available")

    payload = {
        "correlationId": str(payment.correlationId),
        "amount": float(payment.amount),
        "requestedAt": datetime.now(timezone.utc).isoformat()
    }

    # Tenta postar no chosen; se falhar (ex: timeout ou HTTP 5xx) tenta o outro (retry basic)
    processors_try_order = [chosen, "fallback" if chosen == "default" else "default"]

    last_exc = None
    for proc in processors_try_order:
        url = f"{PAYMENT_PROCESSORS[proc]}/payments"
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
            status = resp.status_code
            # Consideramos sucesso qualquer 2xx
            if 200 <= status < 300:
                # grava no banco: processor, status, amount, correlationId, requestedAt, receivedAt
                await record_payment(proc, str(payment.correlationId), float(payment.amount), payload["requestedAt"], status)
                return PaymentResponse(processor=proc, status_code=status, message="ok")
            else:
                # registra falha e continua para tentar o outro
                await record_payment(proc, str(payment.correlationId), float(payment.amount), payload["requestedAt"], status)
                last_exc = Exception(f"HTTP {status} from {proc}")
                # tenta próximo processor
        except Exception as e:
            last_exc = e
            # registra tentativa com status 500 para análise
            await record_payment(proc, str(payment.correlationId), float(payment.amount), payload["requestedAt"], 500)
            # continua e tenta fallback/other
    # Se chegou aqui, todos tentados e falharam
    raise HTTPException(status_code=502, detail=f"All processors failed. Last error: {last_exc}")

# -------------------------
# Endpoint GET /payments-summary
# -------------------------
@app.get("/payments-summary")
async def payments_summary(from_: Optional[str] = None, to: Optional[str] = None):
    """
    Retorna resumo semelhante ao enunciado:
    {
      "default": {"totalRequests": n, "totalAmount": x.xx},
      "fallback": {"totalRequests": m, "totalAmount": y.yy}
    }
    Se from/to forem fornecidos, filtra por intervalo (ISO8601).
    """
    # converte strings para datetime se presentes; a função get_summary_db tratará None como 'tudo'
    result = await get_summary_db(from_, to)
    return result
