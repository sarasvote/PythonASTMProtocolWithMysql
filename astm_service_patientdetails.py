import mysql.connector
from datetime import datetime, date

MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASS = "root"
MYSQL_DB   = "astm_lis"

# ---- Simulated ASTM Message ----
payload = (
    "H|\\^&|||MyLIS^1|||||P|20251102\r"
    "P|1|PAT001||Doe^John^M|M|19800115|||123-4567|Dr.Smith\r"
    "O|1|SMP123||^^^GLU|R|20251102100000|N|||||||||F\r"
    "R|1|^^^GLU|5.6|mmol/L||||N\r"
    "L|1|N\r"
)

# ---- Database setup ----
def ensure_fresh_table():
    conn = mysql.connector.connect(host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASS)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DB} CHARACTER SET utf8mb4")
    conn.database = MYSQL_DB

    # Drop old and recreate fresh table
    cur.execute("DROP TABLE IF EXISTS astm_results")
    cur.execute("""
    CREATE TABLE astm_results (
        id INT AUTO_INCREMENT PRIMARY KEY,
        received_at DATETIME,
        patient_id VARCHAR(50),
        patient_lastname VARCHAR(100),
        patient_firstname VARCHAR(100),
        patient_middle VARCHAR(100),
        patient_sex VARCHAR(10),
        patient_dob DATE,
        patient_age INT,
        physician VARCHAR(100),
        sample_id VARCHAR(50),
        order_priority VARCHAR(10),
        test_code VARCHAR(50),
        result_value VARCHAR(50),
        result_units VARCHAR(50),
        result_status VARCHAR(10),
        raw_message LONGTEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("[DB] Fresh astm_results table created with patient fields.")

# ---- Parse ASTM Payload ----
def parse_payload(msg):
    lines = [l for l in msg.strip().split("\r") if l]
    data = {
        "patient_id": None, "patient_lastname": None, "patient_firstname": None,
        "patient_middle": None, "patient_sex": None, "patient_dob": None,
        "patient_age": None, "physician": None, "sample_id": None,
        "order_priority": None, "test_code": None, "result_value": None,
        "result_units": None, "result_status": None
    }
    for line in lines:
        f = line.split("|")
        if f[0] == "P":
            data["patient_id"] = f[2]
            if len(f) > 4:
                name_parts = f[4].split("^")
                if len(name_parts) > 0: data["patient_lastname"] = name_parts[0]
                if len(name_parts) > 1: data["patient_firstname"] = name_parts[1]
                if len(name_parts) > 2: data["patient_middle"] = name_parts[2]
            data["patient_sex"] = f[5] if len(f) > 5 else None
            if len(f) > 6 and f[6]:
                try:
                    dob = datetime.strptime(f[6][:8], "%Y%m%d").date()
                    data["patient_dob"] = dob
                    today = date.today()
                    data["patient_age"] = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                except: pass
            data["physician"] = f[10] if len(f) > 10 else None
        elif f[0] == "O":
            data["sample_id"] = f[2]
            data["order_priority"] = f[7] if len(f) > 7 else None
        elif f[0] == "R":
            data["test_code"] = f[2].split("^")[-1]
            data["result_value"] = f[3]
            data["result_units"] = f[4]
            data["result_status"] = f[8] if len(f) > 8 else None
    return data

# ---- Insert into Database ----
def save_result(parsed, raw):
    conn = mysql.connector.connect(host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASS, database=MYSQL_DB)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO astm_results (
            received_at, patient_id, patient_lastname, patient_firstname, patient_middle,
            patient_sex, patient_dob, patient_age, physician, sample_id,
            order_priority, test_code, result_value, result_units, result_status, raw_message
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        datetime.utcnow(), parsed["patient_id"], parsed["patient_lastname"], parsed["patient_firstname"],
        parsed["patient_middle"], parsed["patient_sex"], parsed["patient_dob"], parsed["patient_age"],
        parsed["physician"], parsed["sample_id"], parsed["order_priority"], parsed["test_code"],
        parsed["result_value"], parsed["result_units"], parsed["result_status"], raw
    ))
    conn.commit()
    cur.close()
    conn.close()
    print(f"[DB] Saved patient={parsed['patient_id']} sample={parsed['sample_id']} test={parsed['test_code']}")

# ---- Main ----
def main():
    ensure_fresh_table()
    parsed = parse_payload(payload)
    print("[PARSED]", parsed)
    save_result(parsed, payload)
    print("[DONE] Check 'astm_results' table in MySQL.")

if __name__ == "__main__":
    main()
