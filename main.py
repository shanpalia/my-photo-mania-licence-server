import sqlite3
import random
import string
import hashlib
from fastapi import FastAPI, Request
from pydantic import BaseModel
import razorpay
import smtplib
from email.message import EmailMessage

# ================== FASTAPI APP ==================
app = FastAPI()

# ================== DATABASE ==================
conn = sqlite3.connect("database.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS licences (
    licence_key TEXT PRIMARY KEY,
    email TEXT,
    pc_id TEXT,
    activated INTEGER
)
""")
conn.commit()

# ================== RAZORPAY ==================
RAZORPAY_KEY_ID = "YOUR_RAZORPAY_KEY_ID"
RAZORPAY_KEY_SECRET = "YOUR_RAZORPAY_KEY_SECRET"

client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)

# ================== EMAIL (GMAIL SMTP) ==================
SMTP_EMAIL = "yourgmail@gmail.com"
SMTP_PASSWORD = "YOUR_16_DIGIT_APP_PASSWORD"

def send_licence_email(to_email, licence_key):
    msg = EmailMessage()
    msg["Subject"] = "My Photo Mania – Activation Key"
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email

    msg.set_content(f"""
Thank you for your purchase!

Your Lifetime Licence Key:
{licence_key}

Steps:
1. Open My Photo Mania
2. Click ⚙ Settings → Activate Licence
3. Paste key and activate

Regards,
Shapalia
""")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
        smtp.send_message(msg)

# ================== UTILS ==================
def generate_key():
    parts = ["".join(random.choices(string.ascii_uppercase + string.digits, k=4))
             for _ in range(4)]
    return "MPM-" + "-".join(parts)

# ================== MODELS ==================
class ActivateRequest(BaseModel):
    licence_key: str
    pc_id: str

# ================== API ==================
@app.post("/activate")
def activate(data: ActivateRequest):
    cur.execute(
        "SELECT pc_id, activated FROM licences WHERE licence_key=?",
        (data.licence_key,)
    )
    row = cur.fetchone()

    if not row:
        return {"status": "error", "msg": "Invalid licence key"}

    stored_pc, activated = row

    if activated == 1 and stored_pc != data.pc_id:
        return {
            "status": "error",
            "msg": "Licence already used on another PC"
        }

    cur.execute(
        "UPDATE licences SET pc_id=?, activated=1 WHERE licence_key=?",
        (data.pc_id, data.licence_key)
    )
    conn.commit()

    return {"status": "ok", "msg": "Licence activated successfully"}

# ================== RAZORPAY WEBHOOK ==================
@app.post("/razorpay/webhook")
async def razorpay_webhook(request: Request):
    payload = await request.json()

    if payload.get("event") == "payment.captured":
        email = payload["payload"]["payment"]["entity"].get("email")

        if email:
            licence_key = generate_key()

            cur.execute(
                "INSERT INTO licences VALUES (?, ?, ?, ?)",
                (licence_key, email, "", 0)
            )
            conn.commit()

            send_licence_email(email, licence_key)
            print("Licence sent to:", email)

    return {"status": "ok"}
