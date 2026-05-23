"""Utility functions for standard HTTP JSON responses."""

from django.http import JsonResponse


def json_success(payload_data=None, status_code=200):
    """Return a successful JSON response with optional payload."""

    response_data = {"status": "ok"}
    if payload_data:
        response_data.update(payload_data)
    return JsonResponse(response_data, status=status_code)


def json_error(error_message, status_code=400):
    """Return an error JSON response with a specified message."""

    return JsonResponse({"status": "error", "message": error_message}, status=status_code)