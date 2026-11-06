from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.vehicle_list_view, name='vehicle_list'),
    path('marques/', views.brand_list_view, name='brand_list'),
    path('marques/<slug:slug>/', views.brand_detail_view, name='brand_detail'),
    path('<slug:slug>/', views.vehicle_detail_view, name='vehicle_detail'),
]
