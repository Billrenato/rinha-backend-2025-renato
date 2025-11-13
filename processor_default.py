from fastapi import FastAPI
from pydantic import BaseModel
import random

app = FastAPI(title="Processor Default")

class PaymentRequest(BaseModel):
    correlationId: str
    amount: float

@app.post("/payments")
async def pay(request: PaymentRequest):
    # 80% de chance de sucesso (simula instabilidade real)
    if random.random() < 0.8:
        return {"status": "success", "processor": "default"}
    else:
        return {"status": "failed", "processor": "default"}

@app.get("/payments/service-health")
async def health():
    return {"failing": random.random() > 0.8, "minResponseTime": random.randint(1, 50)}
