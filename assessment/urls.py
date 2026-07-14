from django.urls import path
from . import views

urlpatterns = [
    
    path('api/orders/summary/', views.OrderSummaryAPIView.as_view(), name='order-summary'),
]