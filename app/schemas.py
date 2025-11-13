"""
Schemas Pydantic (separados do main.py)
"""
from pydantic import BaseModel, Field
import uuid
from typing import Optional

class PaymentIn(BaseModel):
    correlationId: uuid.UUID = Field(..., description="UUID único da requisição")
    amount: float = Field(..., gt=0, description="Valor do pagamento")

class PaymentResponse(BaseModel):
    processor: str
    status_code: int
    message: Optional[str] = None
