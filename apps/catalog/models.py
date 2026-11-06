from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify


class Brand(models.Model):
    """
    Automotive Marque / Manufacturer representation (e.g. Bugatti, Ferrari, Rolls-Royce).
    """
    name = models.CharField(max_length=100, unique=True, help_text="Marque name")
    slug = models.SlugField(max_length=120, unique=True, help_text="URL-friendly identifier")
    country = models.CharField(max_length=100, blank=True, help_text="Country of origin")
    founded_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1800), MaxValueValidator(2100)],
        help_text="Year the marque was established"
    )
    description = models.TextField(blank=True, help_text="Brand heritage and philosophy")
    logo = models.ImageField(upload_to='brands/logos/', blank=True, null=True, help_text="Marque emblem/logo")
    hero_image = models.ImageField(upload_to='brands/heroes/', blank=True, null=True, help_text="Atelier hero showcase banner")
    is_active = models.BooleanField(default=True, help_text="Visible in catalog and navigation")
    order = models.PositiveIntegerField(default=0, help_text="Display priority order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Marque'
        verbose_name_plural = 'Marques'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def vehicle_count(self):
        return self.vehicles.count()


class Vehicle(models.Model):
    """
    Supercar / Hypercar inventory model.
    """
    STATUS_AVAILABLE = 'available'
    STATUS_RESERVED = 'reserved'
    STATUS_SOLD = 'sold'
    STATUS_INCOMING = 'incoming'

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, 'Available in Atelier'),
        (STATUS_RESERVED, 'Reserved'),
        (STATUS_SOLD, 'Acquired / Sold'),
        (STATUS_INCOMING, 'Incoming Provenance'),
    ]

    FUEL_PETROL = 'petrol'
    FUEL_HYBRID = 'hybrid'
    FUEL_ELECTRIC = 'electric'
    FUEL_DIESEL = 'diesel'

    FUEL_CHOICES = [
        (FUEL_PETROL, 'Petrol'),
        (FUEL_HYBRID, 'Hybrid'),
        (FUEL_ELECTRIC, 'All-Electric'),
        (FUEL_DIESEL, 'Diesel'),
    ]

    TRANSMISSION_AUTOMATIC = 'automatic'
    TRANSMISSION_MANUAL = 'manual'
    TRANSMISSION_SEQUENTIAL = 'sequential'

    TRANSMISSION_CHOICES = [
        (TRANSMISSION_AUTOMATIC, 'Dual-Clutch / Automatic'),
        (TRANSMISSION_MANUAL, 'Manual Transmission'),
        (TRANSMISSION_SEQUENTIAL, 'Sequential Racing'),
    ]

    # Core Identifiers
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name='vehicles',
        help_text="Marque manufacturer"
    )
    model_name = models.CharField(max_length=150, help_text="Model designation (e.g. Chiron Super Sport)")
    slug = models.SlugField(max_length=180, unique=True, help_text="URL slug for vehicle detail")
    vin = models.CharField(
        max_length=17,
        unique=True,
        null=True,
        blank=True,
        help_text="17-character Vehicle Identification Number"
    )
    year = models.PositiveIntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
        help_text="Model production year"
    )

    # Narrative & Curation
    headline = models.CharField(max_length=255, blank=True, help_text="Short luxury tagline")
    description = models.TextField(help_text="Comprehensive vehicle overview, provenance, and pedigree")

    # Financial & Commerce Attributes
    price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Listed price in specified currency"
    )
    currency = models.CharField(max_length=3, default='USD', help_text="ISO 4217 Currency Code (e.g. USD, EUR, GBP)")

    # Technical Specifications
    mileage = models.PositiveIntegerField(default=0, help_text="Odometer reading in miles")
    fuel_type = models.CharField(max_length=30, choices=FUEL_CHOICES, default=FUEL_PETROL)
    transmission = models.CharField(max_length=30, choices=TRANSMISSION_CHOICES, default=TRANSMISSION_AUTOMATIC)
    engine = models.CharField(max_length=120, blank=True, help_text="Engine specification (e.g. 8.0L Quad-Turbo W16)")
    horsepower = models.PositiveIntegerField(null=True, blank=True, help_text="Brake horsepower (BHP)")
    top_speed_mph = models.PositiveIntegerField(null=True, blank=True, help_text="Top speed in MPH")
    acceleration_0_60 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="0-60 MPH acceleration time in seconds"
    )

    # Aesthetics
    exterior_color = models.CharField(max_length=80, blank=True, help_text="Exterior finish & livery")
    interior_color = models.CharField(max_length=80, blank=True, help_text="Interior upholstery & trim")

    # Commerce State
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_AVAILABLE,
        db_index=True,
        help_text="Current commercial availability"
    )
    is_featured = models.BooleanField(default=False, db_index=True, help_text="Highlight on atelier homepage")

    # Visual Assets
    primary_image = models.ImageField(
        upload_to='vehicles/primary/',
        blank=True,
        null=True,
        help_text="Primary hero photo of vehicle"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'
        indexes = [
            models.Index(fields=['status', 'is_featured']),
            models.Index(fields=['brand', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gt=0),
                name='vehicle_price_gt_zero'
            )
        ]

    def __str__(self):
        return f"{self.year} {self.brand.name} {self.model_name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.year}-{self.brand.name}-{self.model_name}")
        super().save(*args, **kwargs)


class VehicleImage(models.Model):
    """
    High-resolution gallery media associated with a vehicle.
    """
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='gallery_images',
        help_text="Vehicle this image belongs to"
    )
    image = models.ImageField(upload_to='vehicles/gallery/', help_text="Gallery image file")
    caption = models.CharField(max_length=200, blank=True, help_text="Descriptive photo caption or angle")
    order = models.PositiveIntegerField(default=0, help_text="Display ordering sequence")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Gallery Image'
        verbose_name_plural = 'Gallery Images'

    def __str__(self):
        return f"Image for {self.vehicle} (#{self.order})"


class VehicleSpecification(models.Model):
    """
    Categorized technical specification attributes for granular detail breakdown.
    """
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='specifications',
        help_text="Associated vehicle"
    )
    category = models.CharField(
        max_length=80,
        default='Performance',
        help_text="Attribute category (e.g. Aerodynamics, Chassis, Powertrain)"
    )
    name = models.CharField(max_length=120, help_text="Specification name (e.g. Brakes, Monocoque)")
    value = models.CharField(max_length=255, help_text="Specification metric or value")
    order = models.PositiveIntegerField(default=0, help_text="Display sequence")

    class Meta:
        ordering = ['category', 'order', 'name']
        verbose_name = 'Specification'
        verbose_name_plural = 'Specifications'

    def __str__(self):
        return f"{self.category}: {self.name} = {self.value}"
