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
