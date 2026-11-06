from decimal import Decimal
from io import StringIO
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.contrib.admin.sites import site
from django.core.management import call_command
from apps.catalog.models import Brand, Vehicle, VehicleImage, VehicleSpecification


class CatalogModelTests(TestCase):
    def setUp(self):
        self.brand_bugatti = Brand.objects.create(
            name="Bugatti",
            slug="bugatti",
            country="France",
            founded_year=1909,
            description="Molsheim hypercar manufacturer of record.",
            order=1
        )
        self.brand_ferrari = Brand.objects.create(
            name="Ferrari",
            slug="ferrari",
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

    def test_seed_marques_command(self):
        out = StringIO()
        call_command('seed_marques', stdout=out)
        output = out.getvalue()
        self.assertIn("Marque synchronization complete", output)
        self.assertEqual(Brand.objects.count(), 6)


class CatalogViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.brand_bugatti = Brand.objects.create(
            name="Bugatti",
            slug="bugatti",
            country="France",
            order=1
        )
        self.brand_porsche = Brand.objects.create(
            name="Porsche",
            slug="porsche",
            country="Germany",
            order=2
        )

        # Create multiple vehicles
        self.v1 = Vehicle.objects.create(
            brand=self.brand_bugatti,
            model_name="Chiron Profilée",
            slug="chiron-profilee",
            year=2023,
            description="One-of-a-kind bespoke hypercar.",
            price=Decimal("10800000.00"),
            engine="8.0L W16",
            status=Vehicle.STATUS_AVAILABLE,
            is_featured=True
        )
        self.v2 = Vehicle.objects.create(
            brand=self.brand_porsche,
            model_name="911 GT3 RS",
            slug="911-gt3-rs",
            year=2024,
            description="Naturally aspirated motorsport road racer.",
            price=Decimal("245000.00"),
            engine="4.0L Flat-6",
            status=Vehicle.STATUS_AVAILABLE
        )
        self.v3 = Vehicle.objects.create(
            brand=self.brand_bugatti,
            model_name="Bolide",
            slug="bugatti-bolide",
            year=2024,
            description="Radical track-only hypercar experiment.",
            price=Decimal("4400000.00"),
            engine="8.0L W16",
            status=Vehicle.STATUS_RESERVED
        )

    def test_vehicle_list_view_status_and_template(self):
        url = reverse('catalog:vehicle_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/vehicle_list.html')
        self.assertContains(response, "Chiron Profilée")
        self.assertContains(response, "911 GT3 RS")

    def test_vehicle_list_search_query(self):
        url = reverse('catalog:vehicle_list')
        response = self.client.get(url, {'q': 'Flat-6'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "911 GT3 RS")
        self.assertNotContains(response, "Chiron Profilée")

    def test_vehicle_list_brand_filter(self):
        url = reverse('catalog:vehicle_list')
        response = self.client.get(url, {'brand': 'porsche'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "911 GT3 RS")
        self.assertNotContains(response, "Chiron Profilée")

    def test_vehicle_list_status_filter(self):
        url = reverse('catalog:vehicle_list')
        response = self.client.get(url, {'status': Vehicle.STATUS_RESERVED})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bolide")
        self.assertNotContains(response, "911 GT3 RS")

    def test_vehicle_list_sorting_price_asc(self):
        url = reverse('catalog:vehicle_list')
        response = self.client.get(url, {'sort': 'price_asc'})
        self.assertEqual(response.status_code, 200)
        vehicles = list(response.context['vehicles'])
        self.assertEqual(vehicles[0], self.v2)  # Porsche is lowest price

    def test_vehicle_list_sorting_price_desc(self):
        url = reverse('catalog:vehicle_list')
        response = self.client.get(url, {'sort': 'price_desc'})
        self.assertEqual(response.status_code, 200)
        vehicles = list(response.context['vehicles'])
        self.assertEqual(vehicles[0], self.v1)  # Chiron is highest price

    def test_vehicle_list_pagination(self):
        # Create additional vehicles to test 9 per page pagination limit
        for i in range(10):
            Vehicle.objects.create(
                brand=self.brand_porsche,
                model_name=f"Porsche Cayman GT4 RS #{i}",
                slug=f"cayman-gt4-rs-{i}",
                year=2023,
                description="High revving sports coupe.",
                price=Decimal("170000.00")
            )
        url = reverse('catalog:vehicle_list')
        response = self.client.get(url)
        self.assertEqual(len(response.context['vehicles']), 9)
        self.assertTrue(response.context['vehicles'].has_next())

        # Page 2
        response_p2 = self.client.get(url, {'page': 2})
        self.assertEqual(len(response_p2.context['vehicles']), 4)  # 3 original + 10 created = 13 total -> 9 + 4

    def test_vehicle_list_empty_state(self):
        url = reverse('catalog:vehicle_list')
        response = self.client.get(url, {'q': 'NonexistentHypercarDesignationXYZ'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Supercars Found in Atelier")

    def test_brand_list_view(self):
        url = reverse('catalog:brand_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/brand_list.html')
        self.assertContains(response, "Bugatti")
        self.assertContains(response, "Porsche")

    def test_brand_detail_view(self):
        url = reverse('catalog:brand_detail', kwargs={'slug': 'bugatti'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/brand_detail.html')
        self.assertContains(response, "Chiron Profilée")

    def test_brand_detail_view_404(self):
        url = reverse('catalog:brand_detail', kwargs={'slug': 'nonexistent-marque'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
