from django.urls import path
from . import views

app_name = 'trustwave'

urlpatterns = [
    # Home and authentication
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registration-pending/', views.registration_pending, name='registration_pending'),
    
    # User dashboard and profile
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    
    # Reports
    path('reports/', views.ReportListView.as_view(), name='report_list'),
    path('report/<int:pk>/', views.ReportDetailView.as_view(), name='report_detail'),
    path('submit-report/', views.submit_report, name='submit_report'),
    path('vote/<int:report_id>/', views.vote_report, name='vote_report'),
    path('ask-question/<int:report_id>/', views.ask_question, name='ask_question'),
    
    # Map
    path('map/', views.map_view, name='map_view'),
    
    # Admin
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/validate-user/<int:user_id>/', views.validate_user, name='validate_user'),
    path('dashboard/refuse-user/<int:user_id>/', views.refuse_user, name='refuse_user'),
    path('dashboard/view-user-documents/<int:user_id>/', views.view_user_documents, name='view_user_documents'),
]

