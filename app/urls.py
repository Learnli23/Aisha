from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('',views.home, name = 'home'),
    path('run_analysis/', views.trigger_analysis, name='trigger_analysis'),
    path('analysis_results/', views.view_analysis_results, name='view_analysis_results'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('attrition_dashboard/', views.risk_level_distribution, name='attrition_dashboard'),
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', views.register_user, name='register'),

]
