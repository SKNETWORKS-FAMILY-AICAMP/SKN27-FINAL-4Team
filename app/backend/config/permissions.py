"""Permissions shared by endpoints that support a local demo flow."""

from django.conf import settings
from rest_framework.permissions import BasePermission


class IsAuthenticatedOrDevelopment(BasePermission):
    """Require a real session outside local development."""

    message = "로그인이 필요한 요청입니다."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated) or settings.DEBUG
