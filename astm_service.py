import socket
import threading
import time
import mysql.connector
from mysql.connector import Error
from fastapi import FastAPI
import uvicorn
import traceback
import json
import sys

# ---------- CONFIG ----------
MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "root"
MYSQL_DB = "astm_lis"
MYSQL_PORT = 3306

TCP_PORT = 5100
USE_SIMULATOR = True

# ---------- DATABASE ----------
def get_db_conn():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        port=MYSQL_PORT
    )

def ensure_database_and_tables():
    """Create database and structured table if not exist."""
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        port=MYSQL_PORT
    )
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DB}")
    conn.commit()
    cur.close()
    conn.close()

    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS astm_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            patient_id VARCHAR(50),
            sample_id VARCHAR(50),
            test_code VARCHAR(50),
            result_value VARCHAR(50),
            unit VARCHAR(20),
            status VARCHAR(10),
            raw_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def save_message(raw, parsed):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO astm_messages 
            (patient_id, sample_id, test_code, result_value, unit, status, raw_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            parsed.get("patient_id"),
            parsed.get("order_id"),
            parsed.get("test_code"),
            parsed.get("result"),
            parsed.get("unit"),
            parsed.get("status"),
            raw
        ))
        conn.commit()
        cur.close()
        conn.close()
        print(f"[db] saved sample={parsed.get('order_id')} test={parsed.get('test_code')} result={parsed.get('result')}")
    except Error as e:
        print("[DB ERROR]", e)

# ---------- ASTM PARSER ----------
def parse_astm(raw_msg: str):
    """Basic ASTM text parser that extracts structured fields."""
    lines = raw_msg.strip().split("\r")
    data = {}
    for line in lines:
        parts = line.split("|")
        if line.startswith("P|"):
            data["patient_id"] = parts[2]
        elif line.startswith("O|"):
            data["order_id"] = parts[2]  # sample ID
        elif line.startswith("R|"):
            data["test_code"] = parts[2].split("^")[-1]
            data["result"] = parts[3]
            data["unit"] = parts[4] if len(parts) > 4 else None
            data["status"] = parts[8] if len(parts) > 8 else None
    return data

# ---------- LISTENER ----------
class InstrumentListener(threading.Thread):
    def __init__(self, host="0.0.0.0", port=TCP_PORT):
        super().__init__(daemon=True)
        self.host = host
        self.port = port

    def run(self):
        print(f"[listener] Listening on {self.host}:{self.port}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen(5)
            while True:
                conn, addr = s.accept()
                print(f"[listener] Connection from {addr}")
                threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()

    def handle_client(self, conn, addr):
        try:
            raw_data = b""
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                raw_data += data
            conn.close()

            if raw_data:
                msg = raw_data.decode(errors="ignore")
                print(f"\n[received] From {addr}:\n{msg}")
                parsed = parse_astm(msg)
                print(f"[parsed] {parsed}\n")
                save_message(msg, parsed)

        except Exception as e:
            print("[listener error]", e)
            traceback.print_exc()

# ---------- SIMULATOR ----------
def send_sample(host="127.0.0.1", port=TCP_PORT):
    hdr = b"H|\\^&|||MyLIS^1|||||P|20251101\r"
    patient = b"P|1|123456||Doe^John\r"
    order = b"O|1|SMP123||^^^GLU\r"
    result = b"R|1|^^^GLU|5.6|mmol/L||||N\r"
    termin = b"L|1|N\r"

    payload = hdr + patient + order + result + termin

    time.sleep(3)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.sendall(payload)
    s.close()
    print("[simulator] Sent ASTM sample message.")

# ---------- FASTAPI ----------
app = FastAPI(title="ASTM Listener API")

@app.get("/messages")
def get_messages():
    conn = get_db_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM astm_messages ORDER BY id DESC LIMIT 10")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# ---------- MAIN ----------
def main():
    try:
        ensure_database_and_tables()
        print(f"[init] Connected to MySQL {MYSQL_USER}@{MYSQL_HOST}:{MYSQL_PORT}, DB={MYSQL_DB}")
    except Exception:
        print("[error] Database initialization failed:")
        traceback.print_exc()
        sys.exit(1)

    listener = InstrumentListener()
    listener.start()
    print("[init] Listener started successfully.")

    if USE_SIMULATOR:
        threading.Thread(target=send_sample, daemon=True).start()

    print("[init] Starting FastAPI server on http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
