from django.http import JsonResponse

def json_success(payload=None, status=200):
    data = {"status": "ok"}
    if payload:
        data.update(payload)
    return JsonResponse(data, status=status)

def json_error(message, status=400):
    return JsonResponse({"status": "error", "message": message}, status=status)

def extract_items_and_modes(data):
    """
    Devuelve (items_list, modes_dict).
    Soporta:
    • Formato v1: [ {...}, {...} ]            → ([...], {})
    • Formato v2: {"items": [...], "modes": {...}}
                                               → ([...], {...})
    """
    if isinstance(data, list):
        return data, {}
    if "items" in data:
        return data.get("items", []), data.get("modes", {})
    raise KeyError("Sin clave 'items' ni lista raíz")
