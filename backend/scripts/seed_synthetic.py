# File: backend/scripts/seed_synthetic.py
"""
Seed a fully synthetic cybercrime dataset for demos and testing.

WHY: Clustering and correlation are only convincing when there is
realistic data to run them against. This script generates plausible
complaint narratives and ingests each through the SAME path the API
uses -- ``entity_service.extract_and_store`` (extract -> normalize ->
occurrence). The planted fraud networks therefore emerge because the
real extractor genuinely found the shared entities, not because we
hand-wrote occurrence rows. That is what makes the demo credible.

ETHICS / SAFETY (non-negotiable for a law-enforcement tool):
- Every value here is FABRICATED. No real victim PII, no real account,
  no real UPI, phone, wallet, or domain.
- Phone numbers use a synthetic 9xxxxxxxxx pattern.
- The data exists solely to demonstrate how the platform connects
  complaints; it must never be presented as real intelligence.

DESIGN: Four designed clusters plus standalone noise cases.
- Cluster A: KYC/UPI scam ring (8 cases). Linked transitively -- some
  cases share only the UPI, others only a phone or account, so union-find
  must do real transitive work to merge them into one network.
- Cluster B: digital-arrest gang (6 cases). Shared phone + mule account.
- Cluster C: loan-app fraud (5 cases). Shared APK domain + Telegram handle.
- Cluster D: crypto investment scam (4 cases). Shared ETH wallet.
- 5 standalone noise cases with unique entities, so NOT everything
  clusters -- this proves the engine discriminates.

USAGE (after the DB is up and an admin exists via seed_admin.py):

    python -m scripts.seed_synthetic

The script is idempotent: if synthetic cases are already present it does
nothing. To wipe previously seeded synthetic cases and re-seed, pass the
opt-in destructive flag:

    python -m scripts.seed_synthetic --reset
"""
import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.init_db import init_db
from app.models.case import Case
from app.models.enums import UserRole
from app.models.user import User
from app.services.entity_service import extract_and_store

# A marker prepended to every synthetic case title so the dataset is
# unambiguously identifiable -- both for humans and for safe --reset.
SYNTHETIC_TITLE_PREFIX = "[SYNTHETIC] "


# --------------------------------------------------------------------------- #
# Dataset definition.
#
# Each case is (title, narrative). The narrative is free text containing the
# planted entities; it is run through the real extractor. Shared values are
# what create the clusters, so they are defined once as constants and reused.
# --------------------------------------------------------------------------- #

# --- Cluster A: KYC / UPI scam ring (shared UPI, with transitive links) ----- #
_A_UPI = "kycupdate@ybl"          # appears across the whole ring
_A_PHONE_1 = "9810012345"          # links the first sub-group
_A_PHONE_2 = "9810054321"          # links the second sub-group
_A_ACCOUNT = "402100123456"        # collection account shared by a sub-group

# --- Cluster B: digital-arrest gang (shared phone + mule account) ----------- #
_B_PHONE = "9733088990"
_B_MULE_ACCOUNT = "915500778899"
_B_IFSC = "HDFC0001234"

# --- Cluster C: loan-app fraud (shared APK domain + Telegram handle) -------- #
_C_DOMAIN = "https://quick-rupee-loan.in/app"
_C_TELEGRAM = "@quickrupeesupport"

# --- Cluster D: crypto investment scam (shared ETH wallet) ------------------ #
_D_WALLET = "0x9f8e7d6c5b4a39281706f5e4d3c2b1a098765432"


def _cluster_a() -> list[tuple[str, str]]:
    """KYC/UPI scam ring: 8 cases, merged transitively by shared entities."""
    return [
        (
            "KYC verification fraud - victim 1",
            f"Victim received a call from {_A_PHONE_1} claiming the bank "
            f"account would be frozen unless KYC was updated. Victim was "
            f"directed to transfer Rs 45000 to UPI {_A_UPI}.",
        ),
        (
            "KYC verification fraud - victim 2",
            f"Complainant was told their card was blocked and asked to pay "
            f"Rs 30000 to {_A_UPI} for reactivation. The caller used the "
            f"number {_A_PHONE_1}.",
        ),
        (
            "KYC verification fraud - victim 3",
            f"A fraudster posing as a bank officer collected Rs 60000 via "
            f"UPI {_A_UPI}. Funds were said to be moved to account "
            f"{_A_ACCOUNT}.",
        ),
        (
            "KYC verification fraud - victim 4",
            f"Victim transferred Rs 25000 to account {_A_ACCOUNT} after a "
            f"call from {_A_PHONE_2} about pending KYC.",
        ),
        (
            "KYC verification fraud - victim 5",
            f"Caller from {_A_PHONE_2} threatened account suspension. Victim "
            f"paid Rs 18000; later another Rs 12000 was demanded.",
        ),
        (
            "KYC verification fraud - victim 6",
            f"Complainant paid Rs 52000 to UPI {_A_UPI} believing it was a "
            f"bank verification charge.",
        ),
        (
            "KYC verification fraud - victim 7",
            f"Fraud amount Rs 40000 sent to {_A_UPI}. Victim also shared an "
            f"OTP after a call from {_A_PHONE_2}.",
        ),
        (
            "KYC verification fraud - victim 8",
            f"Victim was asked to deposit Rs 35000 into account {_A_ACCOUNT} "
            f"to 'unlock' net banking.",
        ),
    ]


def _cluster_b() -> list[tuple[str, str]]:
    """Digital-arrest gang: 6 cases sharing a phone and a mule account."""
    return [
        (
            "Digital arrest scam - victim 1",
            f"Victim received a video call from {_B_PHONE} by a person in "
            f"police uniform alleging a money-laundering case. Victim was "
            f"coerced into transferring Rs 200000 to account "
            f"{_B_MULE_ACCOUNT} (IFSC {_B_IFSC}).",
        ),
        (
            "Digital arrest scam - victim 2",
            f"Caller from {_B_PHONE} claimed a parcel contained contraband "
            f"and demanded Rs 150000 be sent to {_B_MULE_ACCOUNT} for "
            f"'case clearance'.",
        ),
        (
            "Digital arrest scam - victim 3",
            f"Victim kept on a fake interrogation call from {_B_PHONE} for "
            f"three hours and paid Rs 90000 to account {_B_MULE_ACCOUNT}.",
        ),
        (
            "Digital arrest scam - victim 4",
            f"Complainant transferred Rs 175000 to {_B_MULE_ACCOUNT} under "
            f"threat of arrest. IFSC provided was {_B_IFSC}.",
        ),
        (
            "Digital arrest scam - victim 5",
            f"A person claiming to be from the cyber cell called from "
            f"{_B_PHONE} and extracted Rs 60000.",
        ),
        (
            "Digital arrest scam - victim 6",
            f"Victim paid Rs 110000 to account {_B_MULE_ACCOUNT} after being "
            f"shown forged court documents on a call.",
        ),
    ]


def _cluster_c() -> list[tuple[str, str]]:
    """Loan-app fraud: 5 cases sharing an APK domain and a Telegram handle."""
    return [
        (
            "Loan app harassment - victim 1",
            f"Victim installed a loan app from {_C_DOMAIN} and was harassed "
            f"for repayment via Telegram {_C_TELEGRAM} after a small "
            f"disbursal.",
        ),
        (
            "Loan app harassment - victim 2",
            f"Complainant downloaded the APK from {_C_DOMAIN}; contacts were "
            f"leaked and threats were sent from {_C_TELEGRAM}.",
        ),
        (
            "Loan app harassment - victim 3",
            f"Victim received morphed images and demands for Rs 20000 from "
            f"the handle {_C_TELEGRAM}.",
        ),
        (
            "Loan app harassment - victim 4",
            f"The app at {_C_DOMAIN} charged hidden processing fees and the "
            f"agent on {_C_TELEGRAM} demanded more money.",
        ),
        (
            "Loan app harassment - victim 5",
            f"Complainant was threatened over Telegram {_C_TELEGRAM} after "
            f"borrowing through {_C_DOMAIN}.",
        ),
    ]


def _cluster_d() -> list[tuple[str, str]]:
    """Crypto investment scam: 4 cases sharing one ETH wallet."""
    return [
        (
            "Crypto investment scam - victim 1",
            f"Victim was promised 30 percent monthly returns and sent crypto "
            f"worth Rs 300000 to wallet {_D_WALLET}.",
        ),
        (
            "Crypto investment scam - victim 2",
            f"Complainant transferred funds to wallet {_D_WALLET} via a fake "
            f"trading platform and could not withdraw.",
        ),
        (
            "Crypto investment scam - victim 3",
            f"Victim deposited Rs 120000 of USDT, ultimately routed to "
            f"{_D_WALLET}.",
        ),
        (
            "Crypto investment scam - victim 4",
            f"After an initial fake 'profit', victim sent a further Rs 90000 "
            f"to {_D_WALLET}.",
        ),
    ]


def _noise_cases() -> list[tuple[str, str]]:
    """Standalone cases with unique entities -- must NOT cluster."""
    return [
        (
            "OLX delivery scam - standalone",
            "Victim paid Rs 8000 advance to UPI olxdeal9@okaxis for a "
            "second-hand bike that never arrived. Caller used 9871100001.",
        ),
        (
            "Fake job offer - standalone",
            "Complainant paid Rs 15000 registration to account 778812340099 "
            "for a work-from-home job that did not exist.",
        ),
        (
            "Electricity bill scam - standalone",
            "Victim received an SMS to pay Rs 1200 via UPI powerbill@ibl to "
            "avoid disconnection; number used was 9123440055.",
        ),
        (
            "Matrimonial fraud - standalone",
            "Complainant was befriended online and sent Rs 50000 to UPI "
            "groomgift@oksbi before the profile vanished.",
        ),
        (
            "Lottery prize scam - standalone",
            "Victim was told they won Rs 25 lakh and paid Rs 9000 'tax' to "
            "account 660055447788 via a call from 9001239876.",
        ),
    ]


def _all_cases() -> list[tuple[str, str]]:
    """Assemble the full synthetic dataset."""
    cases: list[tuple[str, str]] = []
    cases += _cluster_a()
    cases += _cluster_b()
    cases += _cluster_c()
    cases += _cluster_d()
    cases += _noise_cases()
    return cases


def _find_admin(db: Session) -> User | None:
    """Return the first active SYSTEM_ADMIN to author the synthetic cases."""
    return db.scalar(
        select(User)
        .where(User.role == UserRole.SYSTEM_ADMIN, User.is_active.is_(True))
        .order_by(User.id)
    )


def _existing_synthetic(db: Session) -> list[Case]:
    """Return previously seeded synthetic cases (identified by title prefix)."""
    return list(
        db.scalars(
            select(Case).where(Case.title.like(f"{SYNTHETIC_TITLE_PREFIX}%"))
        )
    )


def _reset_synthetic(db: Session) -> int:
    """Delete previously seeded synthetic cases. Returns how many were removed.

    Entity occurrences cascade away with the case (ON DELETE CASCADE). Global
    Entity rows are intentionally left in place: they are de-duplicated and may
    be referenced elsewhere; orphans are harmless and cheap.
    """
    existing = _existing_synthetic(db)
    for case in existing:
        db.delete(case)
    db.flush()
    return len(existing)


def seed(db: Session, *, reset: bool) -> int:
    """Seed the synthetic dataset. Returns a process exit code."""
    admin = _find_admin(db)
    if admin is None:
        print(
            "ERROR: no active SYSTEM_ADMIN found. Run scripts.seed_admin first.",
            file=sys.stderr,
        )
        return 2

    if reset:
        removed = _reset_synthetic(db)
        print(f"Reset: removed {removed} existing synthetic case(s).")
    elif _existing_synthetic(db):
        print(
            "Synthetic cases already present; nothing to do. "
            "Use --reset to wipe and re-seed."
        )
        return 0

    cases = _all_cases()
    for title, narrative in cases:
        case = Case(
            title=f"{SYNTHETIC_TITLE_PREFIX}{title}",
            description=narrative,
            created_by=admin.id,
        )
        db.add(case)
        db.flush()  # assigns case.id before we link entities to it

        # Ingest through the REAL pipeline so clusters emerge from genuine
        # extraction, not hand-written occurrence rows.
        extract_and_store(db, text=narrative, case_id=case.id)

    db.commit()
    print(f"Seeded {len(cases)} synthetic cases authored by '{admin.username}'.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed a synthetic cybercrime dataset (demo/testing only)."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Destructive: delete previously seeded synthetic cases first.",
    )
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        return seed(db, reset=args.reset)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
