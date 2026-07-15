from django.urls import path

from . import views


urlpatterns = [
    path("images/", views.image_collection, name="image-vault-collection"),
    path("images/<int:image_id>/", views.image_detail, name="image-vault-detail"),
]
