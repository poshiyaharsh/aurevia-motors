"""
Django management command to seed comprehensive showcase supercars, technical specifications,
and generate high-resolution atelier media assets across all 6 luxury marques.
Usage:
    python manage.py seed_vehicles
"""

import os
import io
import urllib.request
from decimal import Decimal
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from apps.catalog.models import Brand, Vehicle, VehicleImage, VehicleSpecification


def fetch_and_save_real_car_image(image_url: str, output_path: Path, fallback_args: dict) -> str:
    """
    Downloads high-resolution real supercar photography, resizes it to 1200x800,
    and saves it to the atelier media store. Falls back gracefully to studio render if offline.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(
            image_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            data = response.read()
            img = Image.open(io.BytesIO(data))
            img = img.convert("RGB")
            # High-fidelity resize preserving aspect ratio crop
            target_w, target_h = 1200, 800
            img_ratio = img.width / img.height
            target_ratio = target_w / target_h

            if img_ratio > target_ratio:
                # Wider: crop horizontal edges
                new_w = int(target_ratio * img.height)
                offset = (img.width - new_w) // 2
                img = img.crop((offset, 0, offset + new_w, img.height))
            else:
                # Taller: crop vertical edges
                new_h = int(img.width / target_ratio)
                offset = (img.height - new_h) // 2
                img = img.crop((0, offset, img.width, offset + new_h))

            img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

            # Add subtle luxury gold watermark in lower corner
            draw = ImageDraw.Draw(img)
            draw.text((30, 755), f"AUREVIA MOTORS ATELIER  ◆  {fallback_args.get('marque_name', '').upper()} {fallback_args.get('model_name', '').upper()}", fill=(212, 175, 55))
            
            img.save(output_path, "JPEG", quality=90)
            return str(output_path)
    except Exception as exc:
        # Graceful fallback to procedural studio render
        fallback_args['output_path'] = output_path
        return generate_car_image(**fallback_args)


def generate_car_image(
    marque_name: str,
    model_name: str,
    year: int,
    hp: int,
    top_speed: int,
    accent_color: str,
    view_type: str = "Hero Studio Stance",
    output_path: Path = None
) -> str:
    """
    Generates a dark luxury supercar studio rendering with gold accents and technical typography.
    """
    width, height = 1200, 800
    img = Image.new("RGB", (width, height), color=(10, 12, 16))
    draw = ImageDraw.Draw(img)

    # Gradient radial backdrop simulation
    for r in range(400, 0, -20):
        alpha = int(25 * (1 - r / 400))
        gold_shade = (10 + alpha, 12 + int(alpha * 0.8), 16 + alpha)
        draw.ellipse([600 - r * 1.5, 400 - r, 600 + r * 1.5, 400 + r], outline=gold_shade, width=15)

    # Outer luxury gold framing
    draw.rectangle([20, 20, width - 20, height - 20], outline=(212, 175, 55), width=2)
    draw.rectangle([28, 28, width - 28, height - 28], outline=(40, 48, 64), width=1)

    # Grid horizon line
    draw.line([30, 520, width - 30, 520], fill=(212, 175, 55, 60), width=1)
    for x in range(100, width, 100):
        draw.line([x, 520, int(600 + (x - 600) * 1.8), height - 30], fill=(25, 30, 42), width=1)

    # Silhouette car representation
    draw.polygon([
        (250, 520), (330, 430), (450, 370), (750, 360), 
        (880, 410), (970, 460), (1010, 520), (250, 520)
    ], fill=(18, 22, 31), outline=(212, 175, 55))
    
    # Roofline & Windshield
    draw.polygon([
        (470, 375), (550, 320), (720, 320), (810, 375)
    ], fill=(10, 12, 16), outline=(243, 229, 171))

    # Wheels & Carbon Ceramic Calipers
    draw.ellipse([340, 460, 460, 580], fill=(7, 8, 11), outline=(212, 175, 55), width=3)
    draw.ellipse([375, 495, 425, 545], fill=(20, 24, 34), outline=(243, 229, 171), width=2)
    draw.ellipse([800, 460, 920, 580], fill=(7, 8, 11), outline=(212, 175, 55), width=3)
    draw.ellipse([835, 495, 885, 545], fill=(20, 24, 34), outline=(243, 229, 171), width=2)

    # Lighting signature / Headlamps
    draw.line([970, 460, 1010, 470], fill=(255, 255, 255), width=4)
    draw.line([250, 500, 290, 495], fill=(220, 38, 38), width=4)

    # Atelier Typography & Badging
    draw.text((60, 60), f"AUREVIA MOTORS ATELIER  ◆  CURATION", fill=(212, 175, 55))
    draw.text((60, 85), f"{marque_name.upper()}", fill=(240, 243, 246))
    draw.text((60, 115), f"{year} {model_name.upper()}", fill=(243, 229, 171))
    draw.text((60, 145), f"SPECIFICATION: {view_type.upper()}", fill=(148, 163, 184))

    # Telemetry HUD in lower right
    draw.rectangle([820, 60, 1140, 160], fill=(18, 22, 31), outline=(212, 175, 55), width=1)
    draw.text((840, 75), f"OUTPUT: {hp} HORSEPOWER", fill=(240, 243, 246))
    draw.text((840, 100), f"MAX VELOCITY: {top_speed} MPH", fill=(212, 175, 55))
    draw.text((840, 125), f"LIVERY: {accent_color.upper()}", fill=(148, 163, 184))

    # Watermark
    draw.text((width - 320, height - 55), "CONFIDENTIAL CLIENT PROVENANCE", fill=(60, 70, 90))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=92)
    return str(output_path)


class Command(BaseCommand):
    help = "Seeds 24 flagship luxury supercars and generates studio photography across all marques."

    def handle(self, *args, **options):
        vehicles_catalog = [
            # ---------------- BUGATTI ----------------
            {
                "brand_slug": "bugatti",
                "model_name": "Tourbillon V16 Hybrid",
                "slug": "bugatti-tourbillon-v16",
                "year": 2026,
                "vin": "VF9TB181926001001",
                "headline": "1,800 HP Cosworth V16 Atmospheric Engineering & Horology Aesthetics",
                "description": "The Bugatti Tourbillon completely reimagines the hypercar from a clean slate. Powered by an 8.3-liter naturally aspirated V16 engine developed with Cosworth revving to 9,000 rpm, paired with three electric motors producing 1,800 hp, and featuring an authentic Swiss skeletonized titanium instrument cluster.",
                "price": Decimal("4600000.00"),
                "currency": "USD",
                "mileage": 15,
                "fuel_type": "hybrid",
                "transmission": "automatic",
                "engine": "8.3L Naturally Aspirated V16 + 3 Electric Motors",
                "horsepower": 1800,
                "top_speed_mph": 276,
                "acceleration_0_60": Decimal("2.00"),
                "exterior_color": "Aerolithe Blue & Exposed Deep Blue Carbon",
                "interior_color": "Hermes Ochre Leather & Milled Titanium",
                "status": "available",
                "is_featured": True,
                "specs": [
                    ("Powertrain", "Engine Architecture", "8.3L Naturally Aspirated 90° V16 (Cosworth)"),
                    ("Powertrain", "Electric Motors", "Dual Front Motors (600 hp) + Rear Motor (200 hp)"),
                    ("Horology", "Instrument Cluster", "600-Part Swiss Mechanical Titanium Gauge Assembly"),
                    ("Aero", "Diffuser", "Integral Crash-Structure Diffuser Tunnel"),
                ]
            },
            {
                "brand_slug": "bugatti",
                "model_name": "Chiron Super Sport 300+",
                "slug": "chiron-super-sport-300-plus",
                "year": 2024,
                "vin": "VF9CC381123456789",
                "headline": "The World's First 300+ MPH Production Hypercar Benchmark",
                "description": "Engineered for pure aerodynamic velocity, the Chiron Super Sport 300+ represents the zenith of internal combustion engineering with an 8.0-liter quad-turbocharged W16 engine generating 1,577 horsepower with a dedicated extended Longtail carbon fiber rear profile.",
                "price": Decimal("3900000.00"),
                "currency": "USD",
                "mileage": 120,
                "fuel_type": "petrol",
                "transmission": "automatic",
                "engine": "8.0L Quad-Turbocharged W16",
                "horsepower": 1577,
                "top_speed_mph": 304,
                "acceleration_0_60": Decimal("2.30"),
                "exterior_color": "Jet Black & Jet Orange Livery",
                "interior_color": "Beluga Black Alcantara",
                "status": "available",
                "is_featured": True,
                "specs": [
                    ("Powertrain", "Engine Architecture", "8.0L Quad-Turbo W16"),
                    ("Powertrain", "Power Output", "1,577 bhp @ 7,100 rpm"),
                    ("Aerodynamics", "Body Construction", "Full Carbon Fiber Monocoque & Longtail"),
                    ("Chassis", "Brakes", "Carbon-Ceramic Discs with Titanium Calipers"),
                ]
            },
            {
                "brand_slug": "bugatti",
                "model_name": "W16 Mistral Roadster",
                "slug": "bugatti-w16-mistral",
                "year": 2025,
                "vin": "VF9WM161202500042",
                "headline": "The Ultimate 1,600 HP Open-Top Hypercar Celebration",
                "description": "The final roadgoing incarnation of Bugatti's legendary W16 engine. The Mistral is an open-cockpit roadster delivering unfiltered auditory immersion, bespoke roof scoop ram air ducts, and an aerodynamic X-taillight beam.",
                "price": Decimal("5000000.00"),
                "currency": "USD",
                "mileage": 50,
                "fuel_type": "petrol",
                "transmission": "automatic",
                "engine": "8.0L Quad-Turbocharged W16",
                "horsepower": 1600,
                "top_speed_mph": 261,
                "acceleration_0_60": Decimal("2.40"),
                "exterior_color": "Warm Black & Grand Prix Yellow Accents",
                "interior_color": "Woven Leather & Amber Shifter Inlay",
                "status": "available",
                "is_featured": True,
                "specs": [
                    ("Aero", "Ram Air Intakes", "Dual Roof-Mounted Carbon Air Scoops"),
                    ("Powertrain", "Output", "1,600 PS (1,177 kW)"),
                    ("Lighting", "Tail Unit", "Signature Bugatti X-Wing LED Architecture"),
                ]
            },
            {
                "brand_slug": "bugatti",
                "model_name": "Bolide Track Hypersport",
                "slug": "bugatti-bolide-hypersport",
                "year": 2024,
                "vin": "VF9BL182520240001",
                "headline": "Pure Lightweight Track Weapon: 0.67 kg per Horsepower",
                "description": "Unconstrained by road regulations, the Bolide is Bugatti's track-only experimental titan. Developing 1,825 hp with 110-octane racing fuel and generating nearly 3,000 kg of downforce at top speed.",
                "price": Decimal("4400000.00"),
                "currency": "USD",
                "mileage": 25,
                "fuel_type": "petrol",
                "transmission": "automatic",
                "engine": "8.0L Quad-Turbo W16 (Track Mod)",
                "horsepower": 1825,
                "top_speed_mph": 311,
                "acceleration_0_60": Decimal("2.17"),
                "exterior_color": "French Racing Blue & Raw 3K Carbon",
                "interior_color": "FIA Racing Bucket in Carbon & Blue Race-Tex",
                "status": "reserved",
                "is_featured": False,
                "specs": [
                    ("Chassis", "Dry Weight", "1,240 kg (2,733 lbs)"),
                    ("Aerodynamics", "Morphable Skin", "Active Dimpling Roof Scoop Aerodynamics"),
                    ("Braking", "Carbon Discs", "Brembo F1 Carbon-Carbon 390mm Discs"),
                ]
            },

            # ---------------- LAMBORGHINI ----------------
            {
                "brand_slug": "lamborghini",
                "model_name": "Revuelto V12 Hybrid HPEV",
                "slug": "lamborghini-revuelto-v12-hybrid",
                "year": 2025,
                "vin": "ZHWUE4ZF7PLA12345",
                "headline": "Sant'Agata's First 1,001 HP Electrified High-Performance V12",
                "description": "The Lamborghini Revuelto combines an iconic 6.5-liter naturally aspirated V12 mid-engine with three electric axial-flux motors, establishing a new paradigm in super sports agility and auditory emotion.",
                "price": Decimal("608000.00"),
                "currency": "USD",
                "mileage": 45,
                "fuel_type": "hybrid",
                "transmission": "automatic",
                "engine": "6.5L Naturally Aspirated V12 + 3 Electric Motors",
                "horsepower": 1001,
                "top_speed_mph": 217,
                "acceleration_0_60": Decimal("2.50"),
                "exterior_color": "Arancio Apodis",
                "interior_color": "Nero Ade with Arancio Dryope Stitching",
                "status": "available",
                "is_featured": True,
                "specs": [
                    ("Powertrain", "Combustion Engine", "6.5L Naturally Aspirated V12"),
                    ("Hybrid System", "Battery Capacity", "3.8 kWh Lithium-Ion Monocell"),
                    ("Transmission", "Gearbox", "8-Speed Dual-Clutch Transverse Mounted"),
                ]
            },
            {
                "brand_slug": "lamborghini",
                "model_name": "Sián FKP 37 Supercapacitor",
                "slug": "lamborghini-sian-fkp-37",
                "year": 2021,
                "vin": "ZHWUE3ZF8MLA00019",
                "headline": "World's First Supercapacitor Hybrid Supercar (Limited 1 of 63)",
                "description": "The Sián FKP 37 introduces revolutionary supercapacitor technology storing three times more electrical power than conventional lithium batteries of equal weight, mated to Lamborghini's flagship 774-hp V12.",
                "price": Decimal("3700000.00"),
                "currency": "USD",
                "mileage": 310,
                "fuel_type": "hybrid",
                "transmission": "automatic",
                "engine": "6.5L V12 + 48V Supercapacitor",
                "horsepower": 808,
                "top_speed_mph": 221,
                "acceleration_0_60": Decimal("2.80"),
                "exterior_color": "Verde Gea with Oro Electrum Accents",
                "interior_color": "Terra di Sant'Agata Leather with 3D-Printed Vents",
                "status": "available",
                "is_featured": True,
                "specs": [
                    ("Hybrid", "Storage Device", "Symmetrical Supercapacitor Power Unit"),
                    ("Exclusivity", "Production Cap", "63 Coupes Globally Worldwide"),
                    ("Aero", "Active Cooling Vanes", "Thermal Smart-Material Reactive Flaps"),
                ]
            },
            {
                "brand_slug": "lamborghini",
                "model_name": "Countach LPI 800-4",
                "slug": "lamborghini-countach-lpi-800",
                "year": 2023,
                "vin": "ZHWUE4ZF9NLA00112",
                "headline": "Modern Reimagining of the Original Wedge-Shaped Icon (1 of 112)",
                "description": "Celebrating the 50th anniversary of Marcello Gandini's visionary design, the Countach LPI 800-4 marries modern carbon monocoque architecture and V12 hybrid supercapacitor performance with iconic retro proportions.",
                "price": Decimal("2640000.00"),
                "currency": "USD",
                "mileage": 95,
                "fuel_type": "hybrid",
                "transmission": "automatic",
                "engine": "6.5L V12 + 48V E-Motor",
                "horsepower": 803,
                "top_speed_mph": 221,
                "acceleration_0_60": Decimal("2.80"),
                "exterior_color": "Bianco Siderale with Red Contrast",
                "interior_color": "Rosso & Nero Vintage Leather Upholstery",
                "status": "available",
                "is_featured": False,
                "specs": [
                    ("Bodywork", "Periscopio Roof", "Photocromatic Glass Periscopio Roofline"),
                    ("Chassis", "Drivetrain", "Permanent All-Wheel Drive with Rear-Wheel Steering"),
                ]
            },
            {
                "brand_slug": "lamborghini",
                "model_name": "Huracán Sterrato All-Terrain",
                "slug": "lamborghini-huracan-sterrato",
                "year": 2024,
                "vin": "ZHWUC1ZF5PLA23456",
                "headline": "Rally-Inspired Naturally Aspirated V10 Dirt-Track Supercar",
                "description": "Crafted to conquer loose gravel, desert dunes, and tarmac alike with 44mm increased ride height, aluminum front underbody armor, reinforced sills, and roof-mounted clean air snorkel intake.",
                "price": Decimal("278000.00"),
                "currency": "USD",
                "mileage": 140,
                "fuel_type": "petrol",
                "transmission": "automatic",
                "engine": "5.2L Naturally Aspirated V10",
                "horsepower": 602,
                "top_speed_mph": 162,
                "acceleration_0_60": Decimal("3.40"),
                "exterior_color": "Bianco Phanes Matte & Arancio Details",
                "interior_color": "Alcantara Verde Sterrato with Laser Inscriptions",
                "status": "available",
                "is_featured": False,
                "specs": [
                    ("Suspension", "Ground Clearance", "+44mm Lifted Magnetorheological Suspension"),
                    ("Tires", "Off-Road Compound", "Bridgestone Dueler All-Terrain AT002 Run-Flat"),
                ]
            },

            # ---------------- FERRARI ----------------
            {
                "brand_slug": "ferrari",
                "model_name": "SF90 XX Stradale",
                "slug": "ferrari-sf90-xx-stradale",
                "year": 2024,
                "vin": "ZFF90BFA4R0234567",
                "headline": "The First Road-Legal XX Programme Masterpiece from Maranello",
                "description": "Infused with Ferrari's elite XX track engineering, the SF90 XX Stradale pairs a twin-turbo V8 with Formula 1 tri-motor hybrid technology, crowned by a fixed rear wing delivering 530 kg of downforce at 250 km/h.",
                "price": Decimal("890000.00"),
                "currency": "USD",
                "mileage": 85,
                "fuel_type": "hybrid",
                "transmission": "automatic",
                "engine": "4.0L Twin-Turbo V8 + Tri-Motor Hybrid",
                "horsepower": 1016,
                "top_speed_mph": 199,
                "acceleration_0_60": Decimal("2.30"),
                "exterior_color": "Rosso Corsa Opaco & Flash Orange",
                "interior_color": "Carbon Racing Shells in Technical Fabric",
                "status": "available",
                "is_featured": True,
                "specs": [
                    ("Aero", "Downforce", "530 kg @ 155 mph"),
                    ("Powertrain", "Internal Combustion", "4.0L 90° Twin-Turbo V8 (786 bhp)"),
                    ("Dynamics", "Extra Boost", "F1 Qualifying Mode Power Surge"),
                ]
            },
            {
                "brand_slug": "ferrari",
                "model_name": "Daytona SP3 Icona Series",
                "slug": "ferrari-daytona-sp3",
                "year": 2023,
                "vin": "ZFF92BFA8P0245678",
                "headline": "Homage to the 1967 24 Hours of Daytona 1-2-3 Podium Sweep",
                "description": "Part of Ferrari's ultra-exclusive Icona series, the Daytona SP3 features a mid-rear mounted 829-hp 6.5-liter naturally aspirated V12 singing to 9,500 rpm, encased in sensual Targa carbon fiber architecture.",
                "price": Decimal("2250000.00"),
                "currency": "USD",
                "mileage": 60,
                "fuel_type": "petrol",
                "transmission": "automatic",
                "engine": "6.5L Naturally Aspirated 65° V12 (F140HC)",
                "horsepower": 829,
                "top_speed_mph": 211,
                "acceleration_0_60": Decimal("2.85"),
                "exterior_color": "Rosso Magma with Bianco Historic Livery",
                "interior_color": "Blu Sterling Alcantara Integrated Bucket Seats",
                "status": "available",
                "is_featured": True,
                "specs": [
                    ("Engine", "Max RPM", "9,500 RPM Redline"),
                    ("Structure", "Monocoque", "T1000 Carbon Fiber with Integrated Chassis Seats"),
                ]
            },
            {
                "brand_slug": "ferrari",
                "model_name": "812 Competizione",
                "slug": "ferrari-812-competizione",
                "year": 2023,
                "vin": "ZFF88BFA9P0256789",
                "headline": "The Ultimate Front-Mid 819 HP V12 Berlinetta Evolution",
                "description": "Equipped with independent four-wheel steering, a single-piece aluminum rear screen with vortex generators, and titanium connecting rods, the 812 Competizione is the quintessential high-revving Ferrari V12.",
                "price": Decimal("602000.00"),
                "currency": "USD",
                "mileage": 180,
                "fuel_type": "petrol",
                "transmission": "automatic",
                "engine": "6.5L Naturally Aspirated V12",
                "horsepower": 819,
                "top_speed_mph": 211,
                "acceleration_0_60": Decimal("2.85"),
                "exterior_color": "Grigio Ferro Metallizzato & Giallo Modena Stripe",
                "interior_color": "Charcoal Alcantara & Giallo Accents",
                "status": "available",
                "is_featured": False,
                "specs": [
                    ("Steering", "4-Wheel Steering", "Independent Virtual Short Wheelbase 3.0"),
                    ("Aero", "Rear Vortex Screen", "Aluminum Blade Aerodynamic Airflow Redirection"),
                ]
            },
            {
                "brand_slug": "ferrari",
                "model_name": "296 GTB Assetto Fiorano",
                "slug": "ferrari-296-gtb-fiorano",
                "year": 2024,
                "vin": "ZFF96BFA2R0267890",
                "headline": "Fun to Drive Defined: 120° Wide-Angle V6 Hybrid Architecture",
                "description": "Nicknamed the piccolo V12 due to its evocative soundtrack, the 296 GTB Assetto Fiorano pairs a compact twin-turbo V6 with a rear electric motor producing 819 hp, optimized with Multimatic racing dampers and Lexan rear screen.",
                "price": Decimal("342000.00"),
                "currency": "USD",
                "mileage": 310,
                "fuel_type": "hybrid",
                "transmission": "automatic",
                "engine": "3.0L 120° Twin-Turbo V6 + Electric Motor",
                "horsepower": 819,
                "top_speed_mph": 205,
                "acceleration_0_60": Decimal("2.90"),
                "exterior_color": "Corsa Blue with Argento Nürburgring Racing Stripe",
                "interior_color": "Cuoio Natural Hide & Carbon Center Console",
                "status": "available",
                "is_featured": False,
                "specs": [
                    ("Dampers", "Track Tuning", "Fixed-Rate Multimatic GT Racing Dampers"),
                    ("Weight Reduction", "Carbon Package", "-15 kg Assetto Fiorano Composite Package"),
                ]
            },

            # ---------------- ROLLS-ROYCE ----------------
            {
                "brand_slug": "rolls-royce",
                "model_name": "Spectre All-Electric Coupe",
                "slug": "rolls-royce-spectre-electric",
                "year": 2025,
                "vin": "SCA3S6A08RUX34567",
                "headline": "The World's Preeminent Ultra-Luxury Electric Super Coupe",
                "description": "The spiritual successor to the Phantom Coupe, Spectre represents the culmination of Charles Rolls' prophecy: silent, vibration-free, instantaneous electric propulsion enveloped in Goodwood's architecture of luxury.",
                "price": Decimal("420000.00"),
                "currency": "USD",
                "mileage": 300,
                "fuel_type": "electric",
                "transmission": "automatic",
                "engine": "Dual Separately Excited Synchronous Motors",
                "horsepower": 577,
                "top_speed_mph": 155,
                "acceleration_0_60": Decimal("4.40"),
                "exterior_color": "Chartreuse & Black Diamond Two-Tone",
                "interior_color": "Grace White Leather & Starlight Doors",
                "status": "available",
                "is_featured": True,
                "specs": [
                    ("Propulsion", "Electric Architecture", "Dual Motor All-Wheel Drive"),
                    ("Acoustics", "Cabin Sound Deadening", "700 kg of Acoustic Insulation"),
                    ("Bespoke", "Illuminated Fascia", "5,500 Clustered Optical Stars"),
                ]
            },
            {
                "brand_slug": "rolls-royce",
                "model_name": "Phantom VIII Series II Extended",
                "slug": "rolls-royce-phantom-viii-extended",
                "year": 2024,
                "vin": "SCA1S6804RUX45678",
                "headline": "The Pinnacle of Bespoke Sanctuary & Sovereign Craftsmanship",
                "description": "The flagship of luxury motoring. Extended wheelbase providing an opulent rear passenger haven with privacy suites, refrigerated champagne console, and the iconic 6.75-liter twin-turbo V12 providing effortless waftability.",
                "price": Decimal("540000.00"),
                "currency": "USD",
                "mileage": 450,
                "fuel_type": "petrol",
                "transmission": "automatic",
                "engine": "6.75L Twin-Turbocharged V12",
                "horsepower": 563,
                "top_speed_mph": 155,
                "acceleration_0_60": Decimal("5.10"),
                "exterior_color": "Midnight Sapphire & Silver Satin Bonnet",
                "interior_color": "Seashell & Navy Blue Leather with Open-Pore Walnut",
                "status": "available",
                "is_featured": True,
                "specs": [
                    ("Cabin", "The Gallery", "Hermetically Sealed Bespoke Glass Art Gallery Dashboard"),
                    ("Doors", "Effortless Closure", "Power-Operated Laser-Sensor Coach Doors"),
                ]
            },
            {
                "brand_slug": "rolls-royce",
                "model_name": "Cullinan Series II Black Badge",
                "slug": "rolls-royce-cullinan-black-badge",
                "year": 2025,
                "vin": "SCA3S6B09RUX56789",
                "headline": "The Dark, Alter-Ego Expression of All-Terrain Sovereign Luxury",
                "description": "An unapologetic statement of power and darkness. Features 592 horsepower, darkened chrome Spirit of Ecstasy, technical carbon fiber interior veneer, and an unshakeable magic carpet ride across any landscape.",
                "price": Decimal("450000.00"),
                "currency": "USD",
                "mileage": 180,
                "fuel_type": "petrol",
                "transmission": "automatic",
                "engine": "6.75L Twin-Turbocharged V12",
                "horsepower": 592,
                "top_speed_mph": 155,
                "acceleration_0_60": Decimal("4.90"),
                "exterior_color": "Dark Emerald & Black Badge Carbon Wheels",
                "interior_color": "Forge Yellow & Black Technical Fiber Trim",
                "status": "available",
                "is_featured": False,
                "specs": [
                    ("Tailgate", "Viewing Suite", "Two Leather Lounge Chairs & Cocktail Table in Luggage Compartment"),
                    ("Aesthetic", "Black Badge Spirit", "High-Gloss Vapor-Deposited Dark Chrome Trim"),
                ]
            },
            {
                "brand_slug": "rolls-royce",
                "model_name": "Ghost Black Badge",
                "slug": "rolls-royce-ghost-black-badge",
                "year": 2024,
                "vin": "SCA2S6A07RUX67890",
                "headline": "Minimalist Post-Opulent Grandeur with 592 Horsepower V12 Adrenaline",
                "description": "Ghost Black Badge rejects overt ornamentation in favor of pure architectural serenity, featuring an illuminated Pantheon grille, all-wheel drive, and all-wheel steering for effortless dynamic poise.",
                "price": Decimal("410000.00"),
                "currency": "USD",
                "mileage": 620,
                "fuel_type": "petrol",
                "transmission": "automatic",
                "engine": "6.75L Twin-Turbo V12",
                "horsepower": 592,
                "top_speed_mph": 155,
                "acceleration_0_60": Decimal("4.50"),
                "exterior_color": "Tempest Grey with Mandarin Coachline",
                "interior_color": "Mandarin & Scivaro Grey Monogrammed Hide",
                "status": "available",
                "is_featured": False,
                "specs": [
                    ("Suspension", "Planar System", "Upper Wishbone Damper Unit for Flawless Isolation"),
                    ("Illumination", "Pantheon Grille", "Subtle 20-LED Downlit Radiator Veins"),
                ]
            },

            # ---------------- PORSCHE ----------------
            {
                "brand_slug": "porsche",
                "model_name": "911 GT3 RS (992)",
                "slug": "porsche-911-gt3-rs-992",
                "year": 2024,
                "vin": "WP0AF2A97RS456789",
                "headline": "Motorsport Aerodynamics for the Road — 9,000 RPM Atmospheric Purity",
                "description": "Featuring a massive active rear wing with DRS, central radiator concept, and driver-adjustable differential and rebound settings directly on the steering wheel, the GT3 RS is a street-homologated race weapon.",
                "price": Decimal("315000.00"),
                "currency": "USD",
                "mileage": 420,
                "fuel_type": "petrol",
                "transmission": "automatic",
                "engine": "4.0L Naturally Aspirated Flat-6 (9,000 RPM)",
                "horsepower": 518,
                "top_speed_mph": 184,
                "acceleration_0_60": Decimal("3.00"),
                "exterior_color": "Ice Grey Metallic with Pyro Red Wheels",
                "interior_color": "Weissach Package Carbon Fiber & Race-Tex",
                "status": "available",
                "is_featured": True,
                "specs": [
                    ("Engine", "Displacement", "4.0L Boxer 6-Cylinder"),
                    ("Rev Limit", "Max Redline", "9,000 RPM"),
                    ("Aerodynamics", "Total Downforce", "860 kg @ 177 mph"),
                ]
            },
            {
                "brand_slug": "porsche",
                "model_name": "918 Spyder Weissach Package",
                "slug": "porsche-918-spyder-weissach",
                "year": 2015,
                "vin": "WP0CA2A84FS800412",
                "headline": "Holy Trinity Pioneer: 875 HP Naturally Aspirated V8 Hybrid Icon",
                "description": "The hypercar that redefined electric hybrid performance. Powered by a racing 4.6-liter dry-sump V8 paired with dual electric motors, featuring top-exit exhaust pipes and sub-7-minute Nürburgring pedigree.",
                "price": Decimal("1950000.00"),
                "currency": "USD",
                "mileage": 1450,
                "fuel_type": "hybrid",
                "transmission": "automatic",
                "engine": "4.6L Naturally Aspirated V8 + Dual E-Motors",
                "horsepower": 875,
                "top_speed_mph": 214,
                "acceleration_0_60": Decimal("2.50"),
                "exterior_color": "Liquid Metal Silver & Martini Racing Livery",
                "interior_color": "Onyx Black Leather with Acid Green Piping",
                "status": "available",
                "is_featured": True,
                "specs": [
                    ("Exhaust", "Top Pipes", "Direct Top-Exit Flame-Spitting Titanium Exhaust System"),
                    ("Package", "Weissach", "Magnesium Wheels & Ceramic Wheel Bearings (-41 kg)"),
                ]
            },
            {
                "brand_slug": "porsche",
                "model_name": "911 S/T 60th Anniversary",
                "slug": "porsche-911-st-60th",
                "year": 2024,
                "vin": "WP0AB2A92RS911060",
                "headline": "Purist Mechanical Grandeur: 518 HP GT3 RS Engine with Manual Gearbox",
                "description": "The lightest 992-generation Porsche produced. Combines the high-revving 518 hp engine of the GT3 RS with a bespoke lightweight manual transmission, single-mass flywheel, and discrete understated ducktail wing.",
                "price": Decimal("291000.00"),
                "currency": "USD",
                "mileage": 75,
                "fuel_type": "petrol",
                "transmission": "manual",
                "engine": "4.0L Naturally Aspirated Boxer-6",
                "horsepower": 518,
                "top_speed_mph": 186,
                "acceleration_0_60": Decimal("3.50"),
                "exterior_color": "Shore Blue Metallic with Heritage Design Package",
                "interior_color": "Classic Cognac Semi-Aniline Leather & Pin-Stripe Fabric",
                "status": "available",
                "is_featured": False,
                "specs": [
                    ("Clutch", "Flywheel", "Lightweight Single-Mass Flywheel (-10.5 kg)"),
                    ("Chassis", "Weight", "1,380 kg (3,056 lbs) Curb Weight"),
                ]
            },
            {
                "brand_slug": "porsche",
                "model_name": "Carrera GT V10 Analog Legend",
                "slug": "porsche-carrera-gt-v10",
                "year": 2005,
                "vin": "WP0ZZZ98Z5L001234",
                "headline": "Analog Masterpiece: 5.7L V10 F1 Engine with Beechwood Shift Knob",
                "description": "Originally conceived for Formula 1 racing, the Carrera GT's 5.7-liter naturally aspirated V10 produces an unmistakable wail. Pure analog driving with a carbon-ceramic clutch, carbon monocoque, and zero stability control.",
                "price": Decimal("1650000.00"),
                "currency": "USD",
                "mileage": 3200,
                "fuel_type": "petrol",
                "transmission": "manual",
                "engine": "5.7L Naturally Aspirated 68° V10",
                "horsepower": 603,
                "top_speed_mph": 205,
                "acceleration_0_60": Decimal("3.80"),
                "exterior_color": "GT Silver Metallic",
                "interior_color": "Ascot Brown Terracotta Leather",
                "status": "available",
                "is_featured": False,
                "specs": [
                    ("Clutch", "PCCC", "Porsche Ceramic Composite Clutch (PCCC)"),
                    ("Pedigree", "Heritage", "Birch & Beechwood Gear Knob Paying Tribute to 917 Le Mans"),
                ]
            },

            # ---------------- MCLAREN ----------------
            {
                "brand_slug": "mclaren",
                "model_name": "Senna Track Series",
                "slug": "mclaren-senna-track-series",
                "year": 2023,
                "vin": "SBM12EAA7KW567890",
                "headline": "Purest Connection Between Driver and Track — 800 KG Downforce",
                "description": "Named after legendary F1 champion Ayrton Senna, this ultra-lightweight carbon hypercar produces 800 kg of downforce and features dihedral doors with glazed lower panels for track apex visibility.",
                "price": Decimal("1450000.00"),
                "currency": "USD",
                "mileage": 210,
                "fuel_type": "petrol",
                "transmission": "automatic",
                "engine": "4.0L Twin-Turbocharged V8",
                "horsepower": 789,
                "top_speed_mph": 208,
                "acceleration_0_60": Decimal("2.70"),
                "exterior_color": "Victory Grey with Trophy Orange Accents",
                "interior_color": "Satin Carbon Fiber Monocage III",
                "status": "available",
                "is_featured": True,
                "specs": [
                    ("Chassis", "Monocoque", "McLaren Monocage III Carbon Fiber"),
                    ("Powertrain", "Engine", "M840TR 4.0L Twin-Turbo V8"),
                    ("Weight", "Dry Weight", "1,198 kg (Lightest McLaren Since F1)"),
                ]
            },
            {
                "brand_slug": "mclaren",
                "model_name": "Speedtail Hyper-GT",
                "slug": "mclaren-speedtail-hyper-gt",
                "year": 2021,
                "vin": "SBM11EAA4MW000088",
                "headline": "250 MPH Streamliner Hyper-GT with Central Driving Position (1 of 106)",
                "description": "McLaren's first ever Hyper-GT and spiritual heir to the legendary F1. With a central driving position, elongated carbon aerodynamic bodywork, and flexible active carbon fiber ailerons that bend seamlessly without hinges.",
                "price": Decimal("3100000.00"),
                "currency": "USD",
                "mileage": 140,
                "fuel_type": "hybrid",
                "transmission": "automatic",
                "engine": "4.0L Twin-Turbo V8 + E-Motor",
                "horsepower": 1055,
                "top_speed_mph": 250,
                "acceleration_0_60": Decimal("2.90"),
                "exterior_color": "Volcano Red & Tinted Carbon",
                "interior_color": "Full Aniline Carmine Leather with Central Titanium Throne",
                "status": "available",
                "is_featured": True,
                "specs": [
                    ("Cockpit", "Seating", "Central 1+2 3-Seater Cockpit Architecture"),
                    ("Aero", "Flexible Ailerons", "Patented Seamless Flexible Carbon Fiber Body Ailerons"),
                ]
            },
            {
                "brand_slug": "mclaren",
                "model_name": "P1 GTR Track Series",
                "slug": "mclaren-p1-gtr-track",
                "year": 2016,
                "vin": "SBM10EAA2GW000021",
                "headline": "Track-Homologated 986 HP Hybrid Titan with Fixed Pylon Wing",
                "description": "Built exclusively for track use to celebrate the 20th anniversary of McLaren's 1995 Le Mans victory. Features an onboard air jack system, slick racing tires, Inconel exhaust pipes, and instant torque-fill electric boost.",
                "price": Decimal("2700000.00"),
                "currency": "USD",
                "mileage": 580,
                "fuel_type": "hybrid",
                "transmission": "automatic",
                "engine": "3.8L Twin-Turbo V8 + E-Motor",
                "horsepower": 986,
                "top_speed_mph": 225,
                "acceleration_0_60": Decimal("2.40"),
                "exterior_color": "Yellow & Green Harrods Heritage Le Mans Livery",
                "interior_color": "Monocage II Naked Carbon & F1 Racing Yoke",
                "status": "available",
                "is_featured": False,
                "specs": [
                    ("Wing", "Rear Downforce", "Fixed Carbon Rear Wing with DRS (+660 kg Downforce)"),
                    ("Cockpit", "Steering", "Formula 1 Derived Multifunction Racing Yoke"),
                ]
            },
            {
                "brand_slug": "mclaren",
                "model_name": "750S Spider",
                "slug": "mclaren-750s-spider",
                "year": 2025,
                "vin": "SBM14EAA8SW123456",
                "headline": "The Benchmark Supercar Benchmark Re-engineered for Pure Emotion",
                "description": "30 horsepower more, 30 kilograms lighter, and 15% quicker steering ratio than the celebrated 720S. Retractable Hard Top opens in 11 seconds at speeds up to 31 mph.",
                "price": Decimal("345000.00"),
                "currency": "USD",
                "mileage": 190,
                "fuel_type": "petrol",
                "transmission": "automatic",
                "engine": "4.0L Twin-Turbocharged V8",
                "horsepower": 740,
                "top_speed_mph": 206,
                "acceleration_0_60": Decimal("2.70"),
                "exterior_color": "Sarigan Quartz with Glazed Carbon Accents",
                "interior_color": "Carbon Black Alcantara & McLaren Orange Details",
                "status": "available",
                "is_featured": False,
                "specs": [
                    ("Roof", "Retractable Hardtop", "Ultra-Fast 11-Second One-Touch Electric Carbon RHT"),
                    ("Chassis", "PCC III", "Proactive Chassis Control III Hydraulic Suspension"),
                ]
            },
        ]

        created_count = 0
        updated_count = 0

        media_root = Path(settings.MEDIA_ROOT)
        media_root.mkdir(parents=True, exist_ok=True)

        # Curated collection of high-resolution real supercar photography URLs from Unsplash
        hero_real_images = {
            "bugatti": [
                "https://images.unsplash.com/photo-1544829099-b9a0c07fad1a?w=1200&q=80",
                "https://images.unsplash.com/photo-1600793575654-910699b5e4d4?w=1200&q=80",
                "https://images.unsplash.com/photo-1541348263662-e0c8de4259ba?w=1200&q=80",
                "https://images.unsplash.com/photo-1563720223185-11003d516935?w=1200&q=80",
            ],
            "lamborghini": [
                "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?w=1200&q=80",
                "https://images.unsplash.com/photo-1580414057403-c5f451f30e1c?w=1200&q=80",
                "https://images.unsplash.com/photo-1544636331-e26879cd4d9b?w=1200&q=80",
                "https://images.unsplash.com/photo-1553440569-bcc63803a83d?w=1200&q=80",
            ],
            "ferrari": [
                "https://images.unsplash.com/photo-1583121274602-3e2820c69888?w=1200&q=80",
                "https://images.unsplash.com/photo-1592198084033-aade902d1aae?w=1200&q=80",
                "https://images.unsplash.com/photo-1617814076367-b759c7d7e738?w=1200&q=80",
                "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=1200&q=80",
            ],
            "rolls-royce": [
                "https://images.unsplash.com/photo-1631295868223-63265b40d9e4?w=1200&q=80",
                "https://images.unsplash.com/photo-1563720223523-491ff04651de?w=1200&q=80",
                "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=1200&q=80",
                "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=1200&q=80",
            ],
            "porsche": [
                "https://images.unsplash.com/photo-1614162692292-7ac56d7f7f1e?w=1200&q=80",
                "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=1200&q=80",
                "https://images.unsplash.com/photo-1580273916550-e323be2ae537?w=1200&q=80",
                "https://images.unsplash.com/photo-1502877338535-766e1452684a?w=1200&q=80",
            ],
            "mclaren": [
                "https://images.unsplash.com/photo-1621135802920-133df287f89c?w=1200&q=80",
                "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=1200&q=80",
                "https://images.unsplash.com/photo-1544829099-b9a0c07fad1a?w=1200&q=80",
                "https://images.unsplash.com/photo-1621135802920-133df287f89c?w=1200&q=80",
            ],
        }

        gallery_real_images = [
            # Cockpit / Interior
            "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1200&q=80",
            # Rear Aero / Tail
            "https://images.unsplash.com/photo-1525609004556-c46c7d6cf023?w=1200&q=80",
            # Track Stance / Wheel Detail
            "https://images.unsplash.com/photo-1617531653332-bd46c24f2068?w=1200&q=80",
        ]

        # Keep count of vehicles processed per marque for distinct image assignment
        marque_counter = {}

        for item in vehicles_catalog:
            brand = Brand.objects.get(slug=item["brand_slug"])
            m_slug = item["brand_slug"]
            m_idx = marque_counter.get(m_slug, 0)
            marque_counter[m_slug] = m_idx + 1
            
            # Download and attach high-res real supercar primary hero photograph
            primary_rel_path = f"vehicles/primary/{item['slug']}_hero.jpg"
            primary_full_path = media_root / primary_rel_path
            
            marque_hero_list = hero_real_images.get(m_slug, [])
            hero_url = marque_hero_list[m_idx % len(marque_hero_list)]

            hero_fallback_args = {
                "marque_name": brand.name,
                "model_name": item["model_name"],
                "year": item["year"],
                "hp": item["horsepower"],
                "top_speed": item["top_speed_mph"],
                "accent_color": item["exterior_color"],
                "view_type": "Hero Studio Stance",
            }

            fetch_and_save_real_car_image(
                image_url=hero_url,
                output_path=primary_full_path,
                fallback_args=hero_fallback_args
            )

            vehicle, created = Vehicle.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "brand": brand,
                    "model_name": item["model_name"],
                    "year": item["year"],
                    "vin": item["vin"],
                    "headline": item["headline"],
                    "description": item["description"],
                    "price": item["price"],
                    "currency": item["currency"],
                    "mileage": item["mileage"],
                    "fuel_type": item["fuel_type"],
                    "transmission": item["transmission"],
                    "engine": item["engine"],
                    "horsepower": item["horsepower"],
                    "top_speed_mph": item["top_speed_mph"],
                    "acceleration_0_60": item["acceleration_0_60"],
                    "exterior_color": item["exterior_color"],
                    "interior_color": item["interior_color"],
                    "status": item["status"],
                    "is_featured": item["is_featured"],
                    "primary_image": primary_rel_path,
                }
            )

            # Download and attach 3 rich real gallery media angles
            gallery_angles = [
                ("Cockpit & Bespoke Controls", "cockpit"),
                ("Rear Aerodynamic Profile", "rear_aero"),
                ("Track Stance & Chassis Detail", "track_stance"),
            ]

            for g_idx, (g_caption, g_slug_suffix) in enumerate(gallery_angles):
                gallery_rel_path = f"vehicles/gallery/{item['slug']}_{g_slug_suffix}.jpg"
                gallery_full_path = media_root / gallery_rel_path
                g_url = gallery_real_images[g_idx % len(gallery_real_images)]

                g_fallback_args = {
                    "marque_name": brand.name,
                    "model_name": item["model_name"],
                    "year": item["year"],
                    "hp": item["horsepower"],
                    "top_speed": item["top_speed_mph"],
                    "accent_color": item["exterior_color"],
                    "view_type": g_caption,
                }

                fetch_and_save_real_car_image(
                    image_url=g_url,
                    output_path=gallery_full_path,
                    fallback_args=g_fallback_args
                )

                VehicleImage.objects.update_or_create(
                    vehicle=vehicle,
                    order=g_idx,
                    defaults={
                        "image": gallery_rel_path,
                        "caption": f"{vehicle.model_name} — {g_caption}",
                    }
                )

            # Seed technical specifications
            for idx, (cat, name, val) in enumerate(item["specs"]):
                VehicleSpecification.objects.update_or_create(
                    vehicle=vehicle,
                    category=cat,
                    name=name,
                    defaults={"value": val, "order": idx}
                )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded 24 supercars across all 6 luxury marques with high-res studio assets! "
                f"({created_count} created, {updated_count} synchronized)."
            )
        )
