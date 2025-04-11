from django.contrib import admin
from django.urls import path, include  # include is added here

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tracker/', include('tracker.urls')),  # Include the URLs from the tracker app
]
