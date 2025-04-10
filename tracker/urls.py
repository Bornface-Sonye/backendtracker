from django.urls import path
from . import views

urlpatterns = [
    path('student/search/', views.StudentSearchView.as_view(), name='student_search'),
    path('submit/complaint/', views.ComplaintSubmissionView.as_view(), name='submit_complaint'),
    path('complaint/success/', views.ComplaintSuccessView.as_view(), name='complaint_success'),
]
