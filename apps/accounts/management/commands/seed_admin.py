import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    """
    Management command to initialize or synchronize the primary administrator
    for Aurevia Motors digital atelier.
    Usage:
        python manage.py seed_admin
    """
    help = "Initializes default superuser credentials for atelier operations."

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "concierge@aurevia.com")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "AureviaAdmin2026!")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
            }
        )
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"[Aurevia Admin] Created default superuser: '{username}'")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"[Aurevia Admin] Synchronized superuser credentials for: '{username}'")
            )
