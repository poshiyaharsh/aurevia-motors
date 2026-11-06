import datetime
from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection


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
    except Exception:
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
