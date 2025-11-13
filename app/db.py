"""
Banco simples usando sqlite3 para persistir pagamentos processados.
Usamos run_in_executor para não bloquear o loop async do FastAPI.
Tabela 'payments' armazena tentativas com processor, correlationId, amount, requestedAt, receivedAt, status_code.
"""

import sqlite3
import asyncio
from datetime import datetime
import os
from typing import Optional, Dict, Any

DB_PATH = os.getenv("DB_PATH", "/data/payments.db")

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    processor TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    amount REAL NOT NULL,
    requested_at TEXT,
    received_at TEXT,
    status_code INTEGER,
    created_at TEXT NOT NULL
);
"""

async def init_db():
    """Inicializa o banco e garante tabela criada."""
    loop = asyncio.get_running_loop()

    def init():
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(CREATE_SQL)
        conn.commit()
        conn.close()

    await loop.run_in_executor(None, init)


async def record_payment(
    processor: str,
    correlation_id: str,
    amount: float,
    requested_at: Optional[str],
    status_code: int
) -> None:
    """Grava tentativa de pagamento no banco."""
    loop = asyncio.get_running_loop()
    created_at = datetime.utcnow().isoformat()

    def _insert():
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO payments (
                processor, correlation_id, amount,
                requested_at, received_at, status_code, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (processor, correlation_id, amount, requested_at,
             datetime.utcnow().isoformat(), status_code, created_at)
        )
        conn.commit()
        conn.close()

    await loop.run_in_executor(None, _insert)


async def get_summary_db(from_iso: Optional[str], to_iso: Optional[str]) -> Dict[str, Any]:
    """Retorna resumo de pagamentos por processor, opcionalmente filtrado por data."""
    loop = asyncio.get_running_loop()

    def _query():
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        cur = conn.cursor()
        where_clauses, params = [], []

        if from_iso:
            where_clauses.append("created_at >= ?")
            params.append(from_iso)
        if to_iso:
            where_clauses.append("created_at <= ?")
            params.append(to_iso)

        where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"""
        SELECT processor, COUNT(*) AS totalRequests,
               COALESCE(SUM(amount), 0.0) AS totalAmount
        FROM payments
        {where}
        GROUP BY processor
        """
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()

        result = {
            "default": {"totalRequests": 0, "totalAmount": 0.0},
            "fallback": {"totalRequests": 0, "totalAmount": 0.0},
        }
        for proc, cnt, total in rows:
            result[proc] = {
                "totalRequests": int(cnt),
                "totalAmount": float(total)
            }
        return result

    return await loop.run_in_executor(None, _query)
