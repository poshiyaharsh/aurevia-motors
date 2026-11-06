from django.contrib import admin
from django.utils.html import format_html
from .models import Brand, Vehicle, VehicleImage, VehicleSpecification


class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 1
    fields = ['image', 'caption', 'order', 'created_at']
    readonly_fields = ['created_at']


class VehicleSpecificationInline(admin.TabularInline):
    model = VehicleSpecification
    extra = 2
    fields = ['category', 'name', 'value', 'order']


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'founded_year', 'vehicle_count_display', 'order', 'is_active', 'updated_at']
    list_filter = ['is_active', 'country']
    search_fields = ['name', 'country', 'description']
    list_editable = ['order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']

    def vehicle_count_display(self, obj):
        count = obj.vehicle_count
        return format_html("<strong>{}</strong> vehicle{}", count, "s" if count != 1 else "")
    vehicle_count_display.short_description = "Inventory Count"


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        'model_name',
        'brand',
        'year',
        'formatted_price',
        'status_badge',
        'is_featured',
        'horsepower',
        'created_at'
    ]
    list_filter = [
        'brand',
        'status',
        'is_featured',
        'year',
        'fuel_type',
        'transmission'
    ]
    search_fields = [
        'model_name',
        'vin',
        'brand__name',
        'engine',
        'exterior_color',
        'interior_color'
    ]
    list_editable = ['is_featured']
    prepopulated_fields = {'slug': ('year', 'model_name')}
    autocomplete_fields = ['brand']
    inlines = [VehicleImageInline, VehicleSpecificationInline]
    date_hierarchy = 'created_at'

    fieldsets = (
        ("Core Identity", {
            'fields': (
                ('brand', 'model_name'),
                ('slug', 'vin'),
                ('year', 'headline'),
                'description',
            )
        }),
        ("Commercial & Financial Status", {
            'fields': (
                ('price', 'currency'),
                ('status', 'is_featured'),
            )
        }),
        ("Technical Specifications", {
            'fields': (
                ('engine', 'horsepower'),
                ('top_speed_mph', 'acceleration_0_60'),
                ('transmission', 'fuel_type'),
                'mileage',
            )
        }),
        ("Aesthetics & Media", {
            'fields': (
                ('exterior_color', 'interior_color'),
                'primary_image',
            )
        }),
    )

    def formatted_price(self, obj):
        return f"{obj.currency} {obj.price:,.2f}"
    formatted_price.short_description = "Price"
    formatted_price.admin_order_field = 'price'

    def status_badge(self, obj):
        colors = {
            'available': '#2ea043',
            'reserved': '#d4af37',
            'sold': '#8b949e',
            'incoming': '#58a6ff',
        }
        color = colors.get(obj.status, '#ffffff')
        return format_html(
            '<span style="background-color: {}; color: #0a0c10; font-weight: bold; padding: 3px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    status_badge.admin_order_field = 'status'
