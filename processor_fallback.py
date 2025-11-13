from fastapi import FastAPI
from pydantic import BaseModel
import random

app = FastAPI(title="Processor Fallback")

class PaymentRequest(BaseModel):
    correlationId: str
    amount: float

@app.post("/payments")
async def pay(request: PaymentRequest):
    return {"status": "success", "processor": "fallback"}

@app.get("/payments/service-health")
async def health():
    return {"failing": False, "minResponseTime": random.randint(1, 50)}
