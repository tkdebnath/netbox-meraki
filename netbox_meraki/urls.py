"""
URL patterns for NetBox Meraki plugin
"""
from django.urls import path
from . import views


urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('sync/', views.SyncView.as_view(), name='sync'),
    path('sync/<int:pk>/', views.SyncLogView.as_view(), name='synclog'),
    path('config/', views.ConfigView.as_view(), name='config'),
]
