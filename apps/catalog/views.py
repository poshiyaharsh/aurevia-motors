from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import Brand, Vehicle


def vehicle_list_view(request):
    """
    Public vehicle catalog view with full-text search, marque filtering,
    status filtering, dynamic sorting, and pagination.
    """
    queryset = Vehicle.objects.select_related('brand').all()

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(model_name__icontains=q) |
            Q(brand__name__icontains=q) |
            Q(engine__icontains=q) |
            Q(headline__icontains=q) |
            Q(description__icontains=q) |
            Q(vin__iexact=q)
        )

    # Marque filter
    selected_brand_slug = request.GET.get('brand', '').strip()
    selected_brand = None
    if selected_brand_slug:
        selected_brand = get_object_or_404(Brand, slug=selected_brand_slug, is_active=True)
        queryset = queryset.filter(brand=selected_brand)

    # Status filter
    selected_status = request.GET.get('status', '').strip()
    if selected_status and selected_status in dict(Vehicle.STATUS_CHOICES):
        queryset = queryset.filter(status=selected_status)

    # Sorting
    sort = request.GET.get('sort', 'newest')
    sort_options = {
        'price_asc': ('Price: Low to High', 'price'),
        'price_desc': ('Price: High to Low', '-price'),
        'year_desc': ('Year: Newest First', '-year'),
        'name_asc': ('Model: A to Z', 'model_name'),
        'newest': ('Atelier Curation (Newest)', '-created_at'),
    }

    if sort in sort_options:
        queryset = queryset.order_by(sort_options[sort][1])
    else:
        queryset = queryset.order_by('-created_at')

    # Pagination: 9 supercars per page
    paginator = Paginator(queryset, 9)
    page_number = request.GET.get('page')

    try:
        vehicles_page = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        vehicles_page = paginator.get_page(1)

    # Active marques for filter sidebar
    marques = Brand.objects.filter(is_active=True).order_by('order', 'name')

    # Construct clean query parameters for pagination links
    params = request.GET.copy()
    if 'page' in params:
        del params['page']
    query_string = params.urlencode()

    context = {
        'vehicles': vehicles_page,
        'marques': marques,
        'selected_brand': selected_brand,
        'selected_brand_slug': selected_brand_slug,
        'selected_status': selected_status,
        'status_choices': Vehicle.STATUS_CHOICES,
        'q': q,
        'sort': sort,
        'sort_options': sort_options,
        'query_string': query_string,
        'total_count': queryset.count(),
    }
    return render(request, 'catalog/vehicle_list.html', context)


def brand_list_view(request):
    """
    Showcase of all active luxury automotive marques.
    """
    marques = Brand.objects.filter(is_active=True).order_by('order', 'name')
    context = {
        'marques': marques,
    }
    return render(request, 'catalog/brand_list.html', context)


def brand_detail_view(request, slug):
    """
    Dedicated marque showcase displaying brand heritage and associated supercars.
    """
    brand = get_object_or_404(Brand, slug=slug, is_active=True)
    vehicles = brand.vehicles.all().order_by('-is_featured', '-created_at')

    context = {
        'brand': brand,
        'vehicles': vehicles,
    }
    return render(request, 'catalog/brand_detail.html', context)


def vehicle_detail_view(request, slug):
    """
    Bespoke vehicle detail view with interactive gallery imagery,
    grouped technical specifications, and acquisition status.
    """
    vehicle = get_object_or_404(
        Vehicle.objects.select_related('brand').prefetch_related('gallery_images', 'specifications'),
        slug=slug,
        brand__is_active=True
    )

    # Group specifications by category
    grouped_specs = {}
    for spec in vehicle.specifications.all():
        category = spec.category or 'General'
        grouped_specs.setdefault(category, []).append(spec)

    # Gallery images
    gallery_images = list(vehicle.gallery_images.all())

    # Related atelier supercars (same marque or available atelier models)
    related_vehicles = Vehicle.objects.filter(
        brand=vehicle.brand
    ).exclude(id=vehicle.id).select_related('brand')[:3]

    if not related_vehicles.exists():
        related_vehicles = Vehicle.objects.filter(
            status=Vehicle.STATUS_AVAILABLE
        ).exclude(id=vehicle.id).select_related('brand')[:3]

    context = {
        'vehicle': vehicle,
        'grouped_specs': grouped_specs,
        'gallery_images': gallery_images,
        'related_vehicles': related_vehicles,
    }
    return render(request, 'catalog/vehicle_detail.html', context)

