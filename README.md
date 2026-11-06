# Aurevia Motors

Aurevia Motors is a luxury supercar digital showroom and e-commerce platform featuring elite marques including Bugatti, Lamborghini, Ferrari, Rolls-Royce, Porsche, and McLaren.

## Overview

Aurevia Motors provides a bespoke digital experience for exploring, configuring, and acquiring luxury supercars. The platform is designed with modern web architecture, featuring:

- **Digital Showroom & Catalog**: Dynamic vehicle discovery, comprehensive technical specifications, and high-resolution galleries.
- **Customer Accounts & Profiles**: Personalized client portals and saved configurations.
- **Cart & Order Lifecycle**: Seamless checkout workflow with order tracking and history.
- **Hybrid Payments**: Support for conventional payments and Web3/MetaMask cryptocurrency transactions.
- **Administrative Control**: Robust back-office management for inventory, orders, and inquiries.

## Technology Stack

- **Backend**: Python / Django
- **Frontend**: Django Templates, HTML5, Modern CSS, JavaScript
- **Database**: SQLite (Development) / PostgreSQL (Production)
- **Web3 / Blockchain**: Web3.py, Web3.js, MetaMask Integration
- **Asset Handling**: Pillow
- **Version Control**: Git & GitHub

## Repository Structure

```text
aurevia-motors/
├── config/                  # Django project configuration & root URLs
├── apps/                    # Modular Django applications
│   ├── core/                # Shared utilities & landing views
│   ├── catalog/             # Vehicle inventory & marque showcases
│   ├── accounts/            # Authentication & customer profiles
│   ├── cart/                # Shopping cart functionality
│   ├── orders/              # Checkout & order processing
│   └── payments/            # Traditional & Web3 payment gateway
├── templates/               # Shared presentation templates
├── static/                  # CSS, JavaScript & branding assets
├── media/                   # Dynamic vehicle & media uploads
├── .gitignore               # Ignored runtime, dev & environment files
├── README.md                # Project documentation
└── requirements.txt         # Project dependencies
```

## Getting Started

### Prerequisites

- Python 3.10+
- Git

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/poshiyaharsh/aurevia-motors.git
   cd aurevia-motors
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations and start local development server:**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

## License

All rights reserved. Proprietary and confidential.
