# Scripts

Operational helper scripts.

## seed_admin.py

Creates the first `SYSTEM_ADMIN` account (there is no open registration).
The password is read from the environment, never passed on the command
line, so it does not leak into shell history.

```bash
cd backend
SEED_ADMIN_PASSWORD='choose-a-strong-password' \
  python -m scripts.seed_admin --username admin --full-name 'Site Admin'
```

After seeding, log in via `POST /auth/login` and use the returned token to
provision further users via `POST /users`.

## seed_synthetic.py

Seeds a fully synthetic cybercrime dataset (28 cases) for demos and
testing. Every value is fabricated; the data must never be presented as
real intelligence. Each complaint narrative is ingested through the same
pipeline the API uses (`extract_and_store`), so the planted fraud networks
emerge from genuine entity extraction.

Requires an existing `SYSTEM_ADMIN` (run `seed_admin.py` first), which is
reused as the author of the seeded cases.

```bash
cd backend
python -m scripts.seed_synthetic
```

The script is idempotent: if synthetic cases already exist it does nothing.
To wipe previously seeded synthetic cases and re-seed, use the opt-in
destructive flag:

```bash
python -m scripts.seed_synthetic --reset
```

Designed clusters (to exercise correlation + clustering):

- **Cluster A** - KYC/UPI scam ring (8 cases), linked transitively via a
  shared UPI, phones, and a collection account.
- **Cluster B** - digital-arrest gang (6 cases), shared phone + mule account.
- **Cluster C** - loan-app fraud (5 cases), shared APK domain + Telegram handle.
- **Cluster D** - crypto investment scam (4 cases), shared ETH wallet.
- **5 standalone noise cases** with unique entities, which must NOT cluster.

The dataset's correctness (exactly 4 clusters of the right sizes, no noise
contamination) is locked down by `tests/test_seed_dataset.py`.
