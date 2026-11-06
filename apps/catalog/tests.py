from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.contrib.admin.sites import site
from apps.catalog.models import Brand, Vehicle, VehicleImage, VehicleSpecification


class CatalogModelTests(TestCase):
    def setUp(self):
        self.brand_bugatti = Brand.objects.create(
            name="Bugatti",
            country="France",
            founded_year=1909,
            description="Molsheim hypercar manufacturer of record.",
            order=1
        )
        self.brand_ferrari = Brand.objects.create(
            name="Ferrari",
            country="Italy",
            founded_year=1939,
            description="Scuderia Maranello racing lineage.",
            order=2
        )

    def test_brand_str_and_slug_generation(self):
        self.assertEqual(str(self.brand_bugatti), "Bugatti")
        self.assertEqual(self.brand_bugatti.slug, "bugatti")

    def test_brand_uniqueness(self):
        with self.assertRaises(IntegrityError):
            Brand.objects.create(name="Bugatti", slug="bugatti-dup")

    def test_vehicle_creation_and_relationship(self):
        vehicle = Vehicle.objects.create(
            brand=self.brand_bugatti,
            model_name="Chiron Pur Sport",
            year=2024,
            description="High-downforce agility-focused hypercar.",
            price=Decimal("3800000.00"),
            currency="USD",
            engine="8.0L Quad-Turbo W16",
            horsepower=1500,
            status=Vehicle.STATUS_AVAILABLE
        )
        self.assertEqual(str(vehicle), "2024 Bugatti Chiron Pur Sport")
        self.assertEqual(self.brand_bugatti.vehicle_count, 1)
        self.assertEqual(self.brand_ferrari.vehicle_count, 0)
        self.assertIn("chiron-pur-sport", vehicle.slug)

    def test_brand_protection_on_delete_with_vehicles(self):
        Vehicle.objects.create(
            brand=self.brand_ferrari,
            model_name="SF90 XX Stradale",
            year=2024,
            description="Track-focused plug-in hybrid supercar.",
            price=Decimal("890000.00")
        )
        with self.assertRaises(ProtectedError):
            self.brand_ferrari.delete()

    def test_vehicle_price_validation_negative(self):
        vehicle = Vehicle(
            brand=self.brand_bugatti,
            model_name="Invalid Car",
            year=2024,
            description="Should fail price validation",
            price=Decimal("-100.00")
        )
        with self.assertRaises(ValidationError):
            vehicle.full_clean()

    def test_vehicle_gallery_and_specifications(self):
        vehicle = Vehicle.objects.create(
            brand=self.brand_ferrari,
            model_name="Daytona SP3",
            year=2023,
            description="Icona series homage to 1967 24 Hours of Daytona.",
            price=Decimal("2250000.00")
        )
        # Create Specification
        spec = VehicleSpecification.objects.create(
            vehicle=vehicle,
            category="Engine",
            name="Displacement",
            value="6.5L Naturally Aspirated V12"
        )
        self.assertEqual(str(spec), "Engine: Displacement = 6.5L Naturally Aspirated V12")
        self.assertEqual(vehicle.specifications.count(), 1)

    def test_admin_registration(self):
        self.assertIn(Brand, site._registry)
        self.assertIn(Vehicle, site._registry)
