from django.http import JsonResponse

def json_success(payload=None, status=200):
    data = {"status": "ok"}
    if payload:
        data.update(payload)
    return JsonResponse(data, status=status)

def json_error(message, status=400):
    return JsonResponse({"status": "error", "message": message}, status=status)