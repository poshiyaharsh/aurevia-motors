# Aurevia Motors

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/poshiyaharsh/aurevia-motors)

Aurevia Motors is a luxury supercar digital showroom and e-commerce platform featuring elite marques including Bugatti, Lamborghini, Ferrari, Rolls-Royce, Porsche, and McLaren. Built with Python 3.12 and Django 5.1, featuring automated on-chain EVM payment verification, responsive atelier showroom, and multi-rail escrow settlement.

---

## 🚀 1-Click Free Deployment on Render

You can deploy Aurevia Motors live to the web with 100% free hosting and automatic SSL on [Render](https://render.com):

1. Click the **Deploy to Render** button above (or connect your GitHub fork on [render.com](https://render.com)).
2. Render reads [`render.yaml`](render.yaml) and [`build.sh`](build.sh) automatically.
3. It sets up the Python 3.12 environment, runs migrations, collects compressed WhiteNoise static assets, seeds the 24 hypercars with real studio photography, and gives you a free live `https://<your-subdomain>.onrender.com` URL!

---

## Architecture & Module Boundaries

The project enforces clean separation of concerns across dedicated application packages:

| Application Package | Scope & Responsibility |
|---|---|
| `apps/core` | Base layout, showroom landing views, operational health diagnostics, custom branded error handlers (404/500), and utility management commands. |
| `apps/catalog` *(Phase 02/03)* | Marque specifications, vehicle models, luxury features, pricing attributes, and high-resolution media galleries. |
| `apps/accounts` *(Phase 05)* | Customer authentication, KYC verification, profile administration, and shipping/billing address books. |
| `apps/cart` *(Phase 06)* | High-performance cart management, reservation tokens, and item quantity constraints. |
| `apps/orders` *(Phase 07/09)* | Pricing engine, luxury tax and duty calculations, coupon validation, order lifecycle records, and invoice generation. |
| `apps/payments` *(Phase 08)* | Dual settlement abstraction: traditional card payments and Web3 / MetaMask cryptographically verified transaction rails. |

---

## Configuration & Settings Architecture

Settings are modularized under `config/settings/` for clean environment separation:

- **`config/settings/base.py`**: Common application definitions, middleware pipeline, template processors, authentication password validators, internationalization, and structured console logging.
- **`config/settings/development.py`**: Local development profile with `DEBUG=True`, console email backend, and SQLite database.
- **`config/settings/production.py`**: Security-hardened profile with `DEBUG=False`, strict secret validation, HTTPS redirection, HSTS headers, and secure cookie flags.
- **`config/settings/__init__.py`**: Dynamically switches profiles via `DJANGO_ENV` (defaults to `development`).

---

## Development Setup

### 1. Prerequisites

- Python 3.10+ (Python 3.12 recommended)
- Git 2.30+

### 2. Environment Setup

```bash
# Clone the repository
git clone https://github.com/poshiyaharsh/aurevia-motors.git
cd aurevia-motors

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment configuration file
cp .env.example .env
```

### 3. Database & System Validation

```bash
# Run system checks
python manage.py check

# Apply migrations
python manage.py migrate

# Execute automated tests
python manage.py test
```

### 4. Running the Development Server

```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` for the showroom or `http://127.0.0.1:8000/health/` for real-time system diagnostics.

---

## Database Backup & Migration Safety

Before running any database migrations or schema alterations, take an atomic snapshot:

```bash
# Create an atomic timestamped backup into /backups (gitignored)
python manage.py backup_db
```

### Rollback Strategy
If a migration or bad state needs to be rolled back:
1. Revert to the latest backup file:
   ```bash
   cp backups/db_backup_YYYYMMDD_HHMMSS.sqlite3 db.sqlite3
   ```
2. In Git, revert problematic commits:
   ```bash
   git revert <commit-hash>
   ```

---

## Git Baseline & Branch Strategy

- **`main`**: Production-ready, verified code. Every merge to `main` must pass tests and system checks.
- **`feature/phase-XX`**: Incremental phase implementation branches.
- **Commit Conventions**: Conventional commits formatted as `Phase XX: Description`.

---

## License

All rights reserved. Proprietary and confidential.
