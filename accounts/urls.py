from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('mentor/', views.mentor_dashboard, name='mentor_dashboard'),
    path('student/', views.student_dashboard, name='student_dashboard'),
]
