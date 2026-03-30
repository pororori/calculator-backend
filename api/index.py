import os
import ssl
from urllib.parse import urlparse
import pg8000.native
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def get_conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    p = urlparse(url)
    ctx = ssl.create_default_context()
    return pg8000.native.Connection(
        user=p.username, password=p.password,
        host=p.hostname, port=p.port or 5432,
        database=p.path.lstrip("/"), ssl_context=ctx,
    )

def ensure_table():
    conn = get_conn()
    conn.run("""
        CREATE TABLE IF NOT EXISTS calc_logs (
            id SERIAL PRIMARY KEY,
            ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            a FLOAT NOT NULL,
            b FLOAT NOT NULL,
            result FLOAT NOT NULL
        )
    """)
    conn.close()

def insert_log(a, b, result):
    try:
        conn = get_conn()
        conn.run(
            "INSERT INTO calc_logs (a, b, result) VALUES (:a, :b, :result)",
            a=a, b=b, result=result,
        )
        conn.close()
    except Exception as e:
        print(f"DB insert failed: {e}")


@app.get("/add")
def add(a: float = Query(...), b: float = Query(...)):
    result = a + b
    insert_log(a, b, result)
    return {"result": result}


@app.get("/logs")
def logs(limit: int = Query(20, ge=1, le=100)):
    try:
        ensure_table()
        conn = get_conn()
        rows = conn.run(
            "SELECT id, ts, a, b, result FROM calc_logs ORDER BY id DESC LIMIT :limit",
            limit=limit,
        )
        conn.close()
        return [
            {"id": r[0], "ts": r[1].isoformat(), "a": r[2], "b": r[3], "result": r[4]}
            for r in rows
        ]
    except Exception as e:
        return {"error": str(e)}


@app.post("/init-db")
def init_db():
    try:
        ensure_table()
        return {"ok": True, "message": "calc_logs table ready"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

fastapi
pg8000
