from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('checkout/process/', views.checkout_process_view, name='checkout_process'),
    path('payment/<str:order_number>/', views.payment_detail_view, name='payment_detail'),
    path('payment/<str:order_number>/confirm-wire/', views.payment_confirm_wire_view, name='payment_confirm_wire'),
    path('payment/<str:order_number>/verify-crypto/', views.payment_verify_crypto_view, name='payment_verify_crypto'),
    path('confirmation/<str:order_number>/', views.order_confirmation_view, name='order_confirmation'),
]
