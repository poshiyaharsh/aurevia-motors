# Aurevia Motors — Luxury Supercar Atelier & Digital Showroom

Aurevia Motors is a digital acquisition platform and high-performance automotive showroom engineered for the world's most discerning collectors. Aurevia presents a curated collection of rare hypercars, track specials, and bespoke grand tourers with real-time allocation management, multi-rail financial settlement, and technical dossier visualization.

---

## The Curated Collection

Aurevia Motors curates six of the world's most prestigious automotive marques, representing the pinnacle of atmospheric, forced-induction, hybrid, and electric propulsion:

| Marque | Heritage Origin | Engineering Hallmarks | Flagship Allocations |
|:---|:---|:---|:---|
| **Bugatti** | Molsheim, France | Quad-turbo W16, Cosworth V16 hybrid, 300+ mph aerodynamics | Tourbillon V16, Chiron Super Sport 300+, W16 Mistral, Bolide |
| **Ferrari** | Maranello, Italy | Formula 1 kinetic hybrid tech, twin-turbo V8, naturally aspirated V12 | SF90 XX Stradale, 812 Competizione, Daytona SP3, 296 GTB Assetto Fiorano |
| **Lamborghini** | Sant'Agata Bolognese, Italy | Naturally aspirated V12 hybrid, extreme ALA aerodynamics, V10 naturally aspirated | Revuelto HPEV, Aventador SVJ, Huracán STO, Countach LPI 800-4 |
| **McLaren** | Woking, United Kingdom | Carbon fiber Monocage, twin-turbo V8, active aerodynamics | P1, Senna Track Series, Speedtail Hyper-GT, 750S Spider |
| **Porsche** | Stuttgart, Germany | High-revving flat-six, lightweight Weissach engineering, hybrid pioneers | 918 Spyder Weissach, 911 GT3 RS (992), 911 GT2 RS Clubsport, Carrera GT |
| **Rolls-Royce** | Goodwood, United Kingdom | Twin-turbo V12 waftability, all-electric architecture, Architecture of Luxury | Phantom VIII Series II, Ghost Black Badge, Spectre All-Electric, Cullinan Series II |

---

## Platform Capabilities & Showroom Experience

### 1. Curated Digital Showroom & Faceted Discovery
- **Multi-Parameter Filtering**: Faceted filtering by marque, horsepower tier, aspiration/fuel architecture (petrol, hybrid, electric), transmission, and budget.
- **Dynamic Inventory Counts**: Live inventory counts update dynamically with search queries and faceted filters.
- **Visual Status Tracking**: Visual status badges indicate vehicle state (`Available in Atelier`, `Allocation Reserved`, `Acquired / Sold`).

### 2. Technical Dossiers & Multi-Angle Atelier Media
- **Multi-Angle Studio Gallery**: Every hypercar features high-resolution studio photography across four dedicated perspectives:
  - *Hero Studio Stance*
  - *Cockpit & Bespoke Controls*
  - *Rear Aerodynamic Profile*
  - *Track Stance & Chassis Detail*
- **Comprehensive Mechanical Specifications**: Detailed categorizations covering powertrain, chassis, transmission, forced induction, braking systems, dry weight, and top speed metrics.
- **Provenance & VIN Tracking**: Official vehicle identification numbers (VIN), mileage tracking, exterior livery codes, and bespoke interior appointments.

### 3. Allocation Session Cart & Pricing Engine
- **Server-Authoritative Cart**: Cart state is securely tied to user sessions with inventory boundary constraints.
- **Luxury Tax & Surcharge Computation**: Configurable regional taxation engine calculating subtotal, duties, and grand totals with decimal precision.
- **VIP Allocation Vouchers**: Coupon engine supporting percentage discounts and fixed-amount atelier credits with expiration dates and minimum qualifying balances.

### 4. Dual-Rail Settlement Architecture
- **Concierge Bank Escrow Transfer**: High-value wire settlement workflow with IBAN/SWIFT instructions, anti-tamper wire confirmation reference tracking, and payment verification auditing.
- **Cryptographic Web3 / MetaMask EVM Rail**:
  - Injected Ethereum provider integration (EIP-1193 standard).
  - Automated transaction parameter construction with checksummed receiver contracts.
  - Server-side cryptographic receipt verification querying Ethereum JSON-RPC nodes.
  - Anti-replay protection enforcing unique transaction hashes and matching sender wallet addresses.

### 5. Client Portfolio & Order Dossiers
- **Private Client Profiles**: Secure authentication, personal credentials, and multi-address book management for white-glove transport delivery.
- **Order Lifecycle Transparency**: Real-time status progression from `Pending Escrow` to `Payment Confirmed`, `Atelier Processing`, and `Delivered`.
- **Downloadable Acquisition Dossiers**: Complete printable and archival order invoices documenting allocated VINs, pricing breakdowns, applied credits, and transaction hashes.

### 6. Operational Governance & Anti-Tamper Audit Trail
- **Comprehensive Administration**: Staff interfaces for managing vehicle inventory, technical specifications, brand profiles, and promotional allocations.
- **Immutable Financial Audit Log**: Dedicated `OrderAuditLog` tracking all order status updates, operator identities, timestamped transitions, and tamper-evident wire reference notes.

---

## Technical Architecture

The platform is designed around modular, domain-driven Django applications:

```
aurevia-motors/
├── apps/
│   ├── core/         # Showroom landing, system health checks, branded 404/500 handlers
│   ├── catalog/      # Marques, hypercars, multi-angle media galleries, specifications
│   ├── accounts/     # VIP client authentication, profile management, delivery address book
│   ├── cart/         # High-concurrency session cart & reservation tokens
│   └── orders/       # Order lifecycle state machine, pricing engine, escrow & Web3 settlement
├── config/
│   ├── settings/     # Modularized settings (base, development, production)
│   ├── urls.py       # Global URL routing & media asset dispatching
│   ├── wsgi.py       # WSGI entry point
│   └── asgi.py       # ASGI entry point
├── static/
│   ├── css/style.css # Dark atelier design system with 24K gold accents
│   └── js/main.js    # Gallery switcher, modal controllers, MetaMask Web3 client
└── templates/        # Semantic HTML5 templates
```

### Technology Stack

- **Core Framework**: Python 3.12 / Django 5.1
- **Asset Processing**: Pillow (high-fidelity Lanczos resampling, dynamic aspect-ratio cropping, atelier watermarking)
- **Static Asset Pipeline**: WhiteNoise with Brotli and Gzip compression
- **Web3 Integration**: EIP-1193 MetaMask client bridge with server-side RPC receipt inspection
- **Design System**: Responsive Dark Atelier aesthetic (`#0A0C10` background, `#D4AF37` 24K gold accents, fluid typography, WCAG AA contrast compliance)

---

## Security Architecture

- **Server-Authoritative State**: All financial pricing, discounts, and order totals are computed server-side to prevent client-side manipulation.
- **CSRF & Session Hardening**: Strictly enforced CSRF tokens on all state-mutating requests, HTTP-only secure cookie flags, and session boundary validation.
- **Safe Navigation Controls**: Strict `url_has_allowed_host_and_scheme` validation to guard against open-redirect vulnerabilities.
- **Header Protections**: Clickjacking defense (`X-Frame-Options: DENY`), MIME sniffing prevention (`X-Content-Type-Options: nosniff`), and HSTS enforcement.

---

## Licensing & Provenance

Aurevia Motors is a high-performance demonstration project showcasing enterprise-grade full-stack Python/Django architecture, digital asset presentation, and hybrid Web2/Web3 financial workflows.
