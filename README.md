# Cyber Investigation Intelligence Platform (CIIP)

This repository contains the backend and static frontend for the Cyber Investigation Intelligence Platform.

## 🚀 Presentation Setup Guide

If you are setting up this project to present or demo to an audience, follow these exact steps to ensure a clean, working environment.

### Prerequisites
Before you start, ensure you have the following installed on your machine:
- **Python 3.9+**
- **Docker Desktop** (must be running in the background)

---

### Step 1: Environment Setup
Open a terminal in the `backend` directory and run the following commands to create a clean virtual environment and install the required dependencies:

```powershell
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate the virtual environment (Windows)
.venv\Scripts\activate

# 3. Install the dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
You need an `.env` file to securely store your database connection string and secret key.
If you don't have one, copy the example file:
```powershell
# Copy the example env file
cp .env.example .env
```
*(The defaults in `.env.example` are pre-configured to work perfectly with the local Docker database).*

### Step 3: Start the Database (PostgreSQL)
We use a Docker container to host the PostgreSQL database. This ensures your presentation runs exactly like production without needing to install SQL servers directly on your OS.

```powershell
# Start the database in the background
docker compose up -d
```
*(Tip: You can verify it's running by opening Docker Desktop and looking for the `ciip_db` container).*

### Step 4: Seed the Database
To give a good presentation, you need data. This script will generate synthetic "dummy" cases for you to show off.

```powershell
# Generate 25+ realistic cybercrime cases and extract entities
python -m scripts.seed_synthetic
```
*(Note: You can create your login account directly from the website's login screen).*

### Step 5: Start the Application
Finally, boot up the FastAPI server using the easy startup script.

```powershell
# Start the server
.\start.bat
```

### 🎯 Presenting
Once the server says `Application startup complete.`, open your web browser and navigate to:

👉 **http://127.0.0.1:8000/**

You will see the CIIP login screen. Click **"Create a new account (Dev Only)"** to register your own account and log in automatically. 

**Demo Flow Suggestion:**
1. Log in.
2. Go to the "Search" tab and search for `9876543210` to show the correlation engine.
3. Show the "Clusters" tab to demonstrate how the system groups organized fraud rings.
4. Go to the "Upload Evidence" section, upload a mock PDF, and show how the OCR Review panel lets you verify and correct automated text extraction in real-time.

---

### Teardown (After the Presentation)
To stop the application, press `Ctrl+C` in the terminal where `main.py` is running.

To shut down the database cleanly without losing data:
```powershell
docker compose stop
```

To completely wipe the database and start entirely fresh for a new presentation:
```powershell
docker compose down -v
```
