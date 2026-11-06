import datetime
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection

logger = logging.getLogger('apps.core')


def home_view(request):
    """
    Renders the Aurevia Motors luxury digital showroom landing page.
    """
    marques = [
        {"name": "Bugatti", "tagline": "Pur Sang & Incomparable Performance"},
        {"name": "Lamborghini", "tagline": "Uncompromising Vision & Raw Adrenaline"},
        {"name": "Ferrari", "tagline": "Maranello Racing Heritage & Elegance"},
        {"name": "Rolls-Royce", "tagline": "The Pinnacle of Bespoke Opulence"},
        {"name": "Porsche", "tagline": "Precision Engineering & Timeless Spirit"},
        {"name": "McLaren", "tagline": "Supercar Innovation & Track Precision"},
    ]
    context = {
        "title": "Aurevia Motors — Luxury Supercar Atelier & Digital Showroom",
        "marques": marques,
        "year": datetime.datetime.now().year,
    }
    return render(request, "core/home.html", context)


def health_view(request):
    """
    Health check endpoint returning system operational status.
    Accepts application/json or returns HTML status depending on Accept header or query param.
    """
    db_healthy = True
    try:
        connection.ensure_connection()
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        db_healthy = False

    status_data = {
        "status": "healthy" if db_healthy else "degraded",
        "service": "Aurevia Motors Platform",
        "environment": "development",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    if request.headers.get("Accept") == "application/json" or request.GET.get("format") == "json":
        status_code = 200 if db_healthy else 503
        return JsonResponse(status_data, status=status_code)

    return render(request, "core/health.html", {"health": status_data})


def custom_404_view(request, exception=None):
    """
    Branded luxury 404 Not Found error view.
    """
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"error": "Resource not found", "status_code": 404}, status=404)
    return render(request, "404.html", status=404)


def custom_500_view(request):
    """
    Branded luxury 500 Internal Server Error view.
    """
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"error": "Internal server error", "status_code": 500}, status=500)
    return render(request, "500.html", status=500)
