import os, csv
from datetime import datetime
from crypto_utils import decrypt_str
from models import BankAccount, PaymentAuthorization

PRIVATE_DIR = os.path.abspath("./private/ach")

def _cents12(amount_cents: int) -> str:
    return f"{amount_cents:012d}"

def _cents10(amount_cents: int) -> str:
    return f"{amount_cents:010d}"

def build_daily_csv(batch_date: datetime, created_by: str, default_sec="CCD"):
    """
    Build a debit-only CSV (service class 225) using all PaymentAuthorizations created on batch_date.
    """
    date_folder = batch_date.strftime("%Y-%m-%d")
    yymmdd = batch_date.strftime("%y%m%d")

    start = datetime(batch_date.year, batch_date.month, batch_date.day)
    end   = start.replace(hour=23, minute=59, second=59, microsecond=999999)

    auths = (PaymentAuthorization.query
             .filter(PaymentAuthorization.consented_at >= start,
                     PaymentAuthorization.consented_at <= end)
             .all())
    if not auths:
        raise RuntimeError(f"No authorizations found for {date_folder}")

    out_dir = os.path.join(PRIVATE_DIR, date_folder)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "run-0100.csv")

    total_tx = 0
    total_debit_cents = 0
    batch_debit_cents = 0
    batch_num = 100  # "0100"

    # Build '6' rows, then prepend '5', then write '1'
    batch_rows = []

    for i, pa in enumerate(auths, start=1):
        ba = BankAccount.query.get(pa.bank_account_id)
        routing = decrypt_str(ba.routing_cipher, ba.routing_nonce)  # 9 digits
        account = decrypt_str(ba.account_cipher, ba.account_nonce)  # up to 17 digits

        amount_cents = int(pa.amount_cents)
        total_tx += 1
        total_debit_cents += amount_cents
        batch_debit_cents += amount_cents

        txn_code = "27" if ba.account_type == "checking" else "37"  # debits
        trace = f"{batch_num}{i:011d}"[:15]
        payee_name = (pa.payer_name or "Customer")[:22]
        payee_id = pa.invoice_number[:15]

        batch_rows.append([
            "6",
            txn_code,
            routing,
            account,
            _cents10(amount_cents),
            payee_id,
            payee_name,
            trace,
            ""
        ])

    # '5' batch header: [5, SERVICE_CLASS, CHASE_ACCOUNT, SEC, ENTRY_DESC, DELIVER_BY, BATCH_CREDIT_AMT, BATCH_DEBIT_AMT, BATCH_NUM, TXN_COUNT]
    batch_rows.insert(0, [
        "5",
        "225",                       # all debits
        "TEST-LOCAL-ACCOUNT",        # replace in prod with your Chase account number
        default_sec,                 # CCD (B2B) or PPD (consumer) depending on your use
        "INVOICE",
        yymmdd,
        "000000000000",              # credit amt (none)
        _cents12(batch_debit_cents), # debit amt
        f"{batch_num:03d}",
        f"{total_tx:04d}"
    ])

    file_row = [
        "1",
        "A",
        datetime.now().strftime("%y%m%d"),
        datetime.now().strftime("%H%M"),
        f"{total_tx:06d}",
        "000000000000",
        _cents12(total_debit_cents),
        "0001"  # one batch
    ]

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(file_row)
        w.writerows(batch_rows)

    return out_path
