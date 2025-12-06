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
    
    # Site Name Rules
    path('site-rules/', views.SiteNameRuleListView.as_view(), name='sitenamerule_list'),
    path('site-rules/add/', views.SiteNameRuleCreateView.as_view(), name='sitenamerule_add'),
    path('site-rules/<int:pk>/edit/', views.SiteNameRuleUpdateView.as_view(), name='sitenamerule_edit'),
    path('site-rules/<int:pk>/delete/', views.SiteNameRuleDeleteView.as_view(), name='sitenamerule_delete'),
    
    # Review Management
    path('reviews/', views.ReviewListView.as_view(), name='review_list'),
    path('review/<int:pk>/', views.ReviewDetailView.as_view(), name='review_detail'),
    path('review/<int:pk>/item/<int:item_pk>/action/', views.ReviewItemActionView.as_view(), name='review_item_action'),
]
