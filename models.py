from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
import uuid

db = SQLAlchemy()

def _uuid():
    return str(uuid.uuid4())

class BankAccount(db.Model):
    __tablename__ = "bank_accounts"
    id = db.Column(db.String, primary_key=True, default=_uuid)
    customer_id = db.Column(db.String, nullable=False)
    routing_cipher = db.Column(db.Text, nullable=False)
    routing_nonce  = db.Column(db.Text, nullable=False)
    account_cipher = db.Column(db.Text, nullable=False)
    account_nonce  = db.Column(db.Text, nullable=False)
    account_type   = db.Column(db.String(10), nullable=False)
    last4          = db.Column(db.String(4), nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

class PaymentAuthorization(db.Model):
    __tablename__ = "payment_authorizations"
    id = db.Column(db.String, primary_key=True, default=_uuid)
    customer_id = db.Column(db.String, nullable=False)
    payer_name = db.Column(db.String(120), nullable=False)
    practice_name = db.Column(db.String(120))
    invoice_number = db.Column(db.String(64), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False, default=0)
    consent_version = db.Column(db.String(32), nullable=False)
    consent_snapshot = db.Column(db.Text, nullable=False)
    consent_checkbox = db.Column(db.Boolean, default=True)
    consented_at = db.Column(db.DateTime, default=datetime.utcnow)
    consent_ip  = db.Column(db.String(64))
    bank_account_id = db.Column(db.String, db.ForeignKey("bank_accounts.id"), nullable=False)

class OneTimeLink(db.Model):
    __tablename__ = "one_time_links"
    id = db.Column(db.String, primary_key=True, default=_uuid)
    file_path = db.Column(db.Text, nullable=False)      # e.g. ./private/ach/2025-10-03/run-0100.csv
    expires_at = db.Column(db.DateTime, nullable=False) # naive UTC timestamp is fine for local
    used_at = db.Column(db.DateTime)                    # null until redeemed
    created_by = db.Column(db.String, nullable=False)   # admin id/email

    @staticmethod
    def create(file_path: str, created_by: str, minutes: int = 15) -> str:
        rec = OneTimeLink(
            file_path=file_path,
            created_by=created_by,
            expires_at=datetime.utcnow() + timedelta(minutes=minutes),
        )
        db.session.add(rec)
        db.session.commit()
        return rec.id