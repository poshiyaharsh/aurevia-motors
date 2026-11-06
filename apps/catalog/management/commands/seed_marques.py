"""
Django management command to safely seed the 6 official luxury automotive marques.
Usage:
    python manage.py seed_marques
"""

from django.core.management.base import BaseCommand
from apps.catalog.models import Brand


class Command(BaseCommand):
    help = "Seeds the six official showcase luxury marques (Bugatti, Lamborghini, Ferrari, Rolls-Royce, Porsche, McLaren)."

    def handle(self, *args, **options):
        marques = [
            {
                "name": "Bugatti",
                "slug": "bugatti",
                "country": "France",
                "founded_year": 1909,
                "description": "Pur Sang, unmatched power and peerless French artisanal coachbuilding from Molsheim.",
                "order": 1,
            },
            {
                "name": "Lamborghini",
                "slug": "lamborghini",
                "country": "Italy",
                "founded_year": 1963,
                "description": "Uncompromising Italian design, raw V10/V12 adrenaline, and futuristic Sant'Agata Bolognese architecture.",
                "order": 2,
            },
            {
                "name": "Ferrari",
                "slug": "ferrari",
                "country": "Italy",
                "founded_year": 1939,
                "description": "The quintessential spirit of Maranello motorsport heritage, aerodynamic perfection, and evocative symphony.",
                "order": 3,
            },
            {
                "name": "Rolls-Royce",
                "slug": "rolls-royce",
                "country": "United Kingdom",
                "founded_year": 1904,
                "description": "The supreme arbiter of bespoke luxury, effortless power, and peerless Goodwood craftsmanship.",
                "order": 4,
            },
            {
                "name": "Porsche",
                "slug": "porsche",
                "country": "Germany",
                "founded_year": 1931,
                "description": "Zuffenhausen precision engineering, endurance racing triumph, and iconic timeless silhouette.",
                "order": 5,
            },
            {
                "name": "McLaren",
                "slug": "mclaren",
                "country": "United Kingdom",
                "founded_year": 1963,
                "description": "Formula 1 carbon-composite lineage and relentless pursuit of hypercar aerodynamic agility from Woking.",
                "order": 6,
            },
        ]

        created_count = 0
        updated_count = 0

        for data in marques:
            brand, created = Brand.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "country": data["country"],
                    "founded_year": data["founded_year"],
                    "description": data["description"],
                    "order": data["order"],
                    "is_active": True,
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Marque synchronization complete. {created_count} created, {updated_count} verified/updated."
            )
        )
