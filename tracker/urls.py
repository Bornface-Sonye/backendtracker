from django.urls import path
from . import views

urlpatterns = [
    path('student/', views.StudentSelectView.as_view(), name='student_select'),
    path('complaints/', views.MissingMarkSelectView.as_view(), name='missing_mark_select'),
]
