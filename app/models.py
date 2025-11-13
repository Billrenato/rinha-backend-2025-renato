"""
Modelos SQLAlchemy para referência (não usados diretamente neste template SQLite).
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    correlation_id = Column(String(36), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    processor = Column(String(50), nullable=False, index=True)
    status_code = Column(Integer, nullable=False, default=0)
    requested_at = Column(String(64), nullable=True)
    received_at = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "correlation_id": self.correlation_id,
            "amount": float(self.amount),
            "processor": self.processor,
            "status_code": self.status_code,
            "requested_at": self.requested_at,
            "received_at": self.received_at,
            "created_at": (
                self.created_at.isoformat()
                if isinstance(self.created_at, datetime.datetime)
                else self.created_at
            ),
        }
