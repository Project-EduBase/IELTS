from django.urls import path
from . import views

app_name = 'attempts'

urlpatterns = [
    path('submit/<int:exam_id>/', views.submit_attempt, name='submit_attempt'),
    path('review/<int:attempt_id>/', views.review_attempt, name='review_attempt'),
    path('my-attempts/', views.my_attempts, name='my_attempts'),
    path('pending-reviews/', views.pending_reviews, name='pending_reviews'),
    path('mentor-stats/', views.mentor_stats, name='mentor_stats'),
    path('mentor-student/<int:student_id>/', views.mentor_student_stats, name='mentor_student_stats'),
    path("attempt/<int:attempt_id>/", views.attempt_result, name="attempt_detail"),
]
