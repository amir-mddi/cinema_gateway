from django.contrib import admin
from django.urls import path

from backend.apps.cinema.controllers.health_controller import health
from backend.apps.cinema.controllers.redirect_controller import tracked_redirect

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("out/<str:token>/", tracked_redirect, name="tracked_redirect"),
]
