import os
from dotenv import load_dotenv

load_dotenv()

from datetime import datetime, timezone, timedelta
from flask import (
    Flask, render_template, request, jsonify, flash,
    send_file, abort, url_for, redirect, session
)
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
from models import db, BankAccount, PaymentAuthorization, OneTimeLink
from crypto_utils import encrypt_str
from batch_csv import build_daily_csv


# Flask app
application = Flask(__name__)
application.config["SECRET_KEY"] = os.environ.get("APP_SECRET", "dev-dev-dev")
application.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_URL", "sqlite:///local.db")
application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

application.permanent_session_lifetime = timedelta(minutes=10)

# Init DB
db.init_app(application)
with application.app_context():
    db.create_all()

# -------------------------
# Auth setup (Flask-Login)
# -------------------------
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(application)

ADMIN_USER = os.environ.get("ADMIN_USER", "owner")
ADMIN_PWHASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

class User(UserMixin):
    """Minimal user wrapper. We have a single admin user from .env."""
    def __init__(self, username: str):
        self.id = username

@login_manager.user_loader
def load_user(user_id):
    if user_id == ADMIN_USER:
        return User(ADMIN_USER)
    return None

@application.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", title="Admin Login")

    # POST
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "")

    if username != ADMIN_USER or not ADMIN_PWHASH or not check_password_hash(ADMIN_PWHASH, password):
        return render_template("login.html", title="Login", error="Invalid username or password"), 401

    # success: create user session
    login_user(User(ADMIN_USER))
    session.permanent = True
    # optional: next= query param support
    next_url = request.args.get("next") or url_for("admin_page")
    return redirect(next_url)

@application.route("/logout", methods=["POST", "GET"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@login_manager.unauthorized_handler
def unauthorized():
    flash("Your session has expired, please log in again.", "warning")
    return redirect(url_for("login"))

# -------------------------
# Public pages
# -------------------------
@application.route("/")
def home():
    return render_template("index.html", title="Home - Avika")

@application.route("/about")
def about():
    return render_template("about.html", title="About Us")

@application.route("/pay")
def pay():
    return render_template("pay.html", title="Pay My Bill")

@application.route("/contact")
def contact():
    return render_template("contact.html", title="Contact Us")

@application.route("/pay-patient")
def pay_patient():
    return render_template("pay-patient.html", title="Patient Payment")

@application.route("/find-my-info")
def invoice_help():
    return render_template("find_info.html", title="Find My Info")

@application.post("/contact-form-content")
def contact_form_content():
    data = request.get_json()
    print("=== New Contact Form Submission ===")
    print(data)
    print("===================================")
    return jsonify({"ok": True, "received": data}), 200

#-------------------------------------------------------------------------------------
@application.post("/card-temp")
def card_temp():
    # just echo what they typed so far; no payment yet
    inv   = (request.form.get("invoiceNumber") or "").strip()
    name  = (request.form.get("fullName") or "").strip()
    pract = (request.form.get("practiceName") or "").strip()
    amt_s = (request.form.get("amount") or "0").strip()

    try:
        base_amt = max(0.0, float(amt_s))
    except:
        base_amt = 0.0

    fee = round(base_amt * 0.035, 2)   # 3.5% card fee
    total = round(base_amt + fee, 2)

    return render_template(
        "card_temp.html",
        title="Card Payment (Preview)",
        info={"invoice": inv, "name": name, "practice": pract, "amount": f"{base_amt:.2f}"},
        fee=f"{fee:.2f}",
        total=f"{total:.2f}",
    )
#---------------------------------------------------------------------------------------------

# -------------------------
# Client Payment (ACH)
# -------------------------
@application.route("/pay-client", methods=["GET", "POST"])
def pay_customer():
    if request.method == "GET":
        return render_template("pay-client.html", title="Client Payment")

    # ----- POST: store ACH + consent -----
    form = request.form
    method      = (form.get("method") or "ach").strip().lower()
    full_name   = (form.get("fullName") or "").strip() or "Customer"
    practice    = (form.get("practiceName") or "").strip()
    invoice     = (form.get("invoiceNumber") or "NA").strip()
    amount_str  = (form.get("amount") or "0").strip()

    try:
        amount_cents = int(round(float(amount_str) * 100))
    except Exception:
        return "Invalid amount", 400
    if amount_cents <= 0:
        return "Amount must be greater than zero", 400

    if method != "ach":
        return "Card flow not implemented in this demo", 400

    routing   = (form.get("ach_routing") or "").strip()
    account   = (form.get("ach_account") or "").strip()
    acct_type = (form.get("ach_account_type") or "").strip().lower()

    if len(routing) != 9 or not routing.isdigit():
        return "Invalid routing number (must be 9 digits).", 400
    if not account.isdigit() or not (4 <= len(account) <= 17):
        return "Invalid account number (4–17 digits).", 400
    if acct_type not in ("checking", "savings"):
        return "Select account type (checking/savings).", 400

    r_ct, r_nonce = encrypt_str(routing)
    a_ct, a_nonce = encrypt_str(account)
    last4 = account[-4:]

    ba = BankAccount(
        customer_id=full_name,
        routing_cipher=r_ct, routing_nonce=r_nonce,
        account_cipher=a_ct, account_nonce=a_nonce,
        account_type=acct_type, last4=last4
    )
    db.session.add(ba)
    db.session.flush()

    consent_version  = (form.get("consent_version") or "ach_web_v1.0")
    consent_snapshot = (form.get("consent_snapshot") or "")
    consent_ip       = request.headers.get("X-Forwarded-For", request.remote_addr)

    pa = PaymentAuthorization(
        customer_id=full_name,
        payer_name=full_name,
        practice_name=practice,
        invoice_number=invoice,
        amount_cents=amount_cents,
        consent_version=consent_version,
        consent_snapshot=consent_snapshot,
        consent_checkbox=True,
        consent_ip=consent_ip,
        bank_account_id=ba.id
    )
    db.session.add(pa)
    db.session.commit()

    return render_template(
        "submitted.html",
        title="Payment Details Received",
        last4=last4,
        invoice=invoice,
        amount=f"{amount_cents/100:.2f}"
    )

# -------------------------
# Admin utilities (PROTECTED BY LOGIN)
# -------------------------
@application.route("/admin", methods=["GET"])
@login_required
def admin_page():
    return render_template("admin.html", title="Admin")


@application.post("/admin/build-csv")
@login_required
def admin_build_csv():
    # optional: allow building for a specific date (YYYY-MM-DD)
    qdate = request.args.get("date")
    if qdate:
        try:
            for_date = datetime.strptime(qdate, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format (YYYY-MM-DD)"}), 400
    else:
        for_date = datetime.now(timezone.utc).date()

    out_path = build_daily_csv(for_date, created_by=current_user.id)
    token = OneTimeLink.create(file_path=out_path, created_by=current_user.id, minutes=15)
    return jsonify({"download": url_for("download_token", token=token, _external=False)})


@application.get("/download/<token>")
@login_required
def download_token(token):
    rec = OneTimeLink.query.get(token)
    if not rec:
        abort(404)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if rec.used_at or now > rec.expires_at:
        abort(410)
    if not os.path.isfile(rec.file_path):
        abort(404)
    rec.used_at = now
    db.session.commit()
    filename = os.path.basename(rec.file_path)
    return send_file(rec.file_path, as_attachment=True, download_name=filename, max_age=0)

# -------------------------
# If a page does not exist -> 404
# -------------------------
@application.errorhandler(404)
def not_found(e):
    return render_template("404.html", title="Not Found"), 404

# -------------------------
# Run (local)
# -------------------------
if __name__ == "__main__":
    application.run(host="127.0.0.1", port=5000, debug=True)
