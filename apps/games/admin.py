from django.contrib import admin
from .models import Game, GameItem, ScoringRule
from django import forms
from django.conf import settings
from django.contrib import messages
import zipfile
import os
import json
import requests

# Helper function like in sync_game_data.py
def deep_get(d, path, default=None):
    keys = path.split(".")
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key)
        else:
            return default
    return d if d is not None else default

class GameAdminForm(forms.ModelForm):
    item_images_zip = forms.FileField(
        required=False,
        label="Subir ZIP con imágenes de ítems",
        help_text="Sube un archivo ZIP que contenga imágenes nombradas como '{ID_DEL_ITEM}.png'. Los ítems deben existir previamente."
    )

    class Meta:
        model = Game
        fields = '__all__'

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    form = GameAdminForm
    list_display = ('name', 'slug', 'color', 'active', 'created_at')
    search_fields = ('name', 'slug', 'color')
    list_filter = ('active',)
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'active')
        }),
        ('Visuals', {
            'fields': ('color', 'icon_image', 'background_image')
        }),
        ('API Configuration', {
            'fields': ('data_source_url', 'json_file', 'field_mapping', 'defaults', 'attributes', 'numeric_fields', 'audio_file')
        }),
        ('Subida Masiva de Imágenes de Ítems', {
            'fields': ('item_images_zip',)
        })
    )

    def _process_items(self, request, game, raw_items_list):
        created_count = 0
        updated_count = 0
        errors_processing = []

        for raw in raw_items_list:
            parsed = {}
            for local_field, remote_field in game.field_mapping.items():
                value = deep_get(raw, remote_field, game.defaults.get(local_field))
                parsed[local_field] = value

            # Ensure original 'id' from source data is preserved in 'data' if it exists
            original_id_from_source = deep_get(raw, 'id')
            if original_id_from_source is not None:
                parsed['id'] = original_id_from_source
            
            # Determine the name for the GameItem
            # Uses field_mapping first, then common default names
            name_field_in_mapping = None
            for k, v in game.field_mapping.items():
                if k == 'name' or k == 'nombre': # Check if 'name' or 'nombre' is mapped
                    name_field_in_mapping = v
                    break
            
            if name_field_in_mapping:
                name = deep_get(raw, name_field_in_mapping)
            else: # Fallback to common direct names if not in mapping or mapping doesn't specify name source
                name = raw.get("name") or raw.get("nombre")

            if not name:
                errors_processing.append(f"Item skipped: missing name. Data: {str(raw)[:100]}")
                continue

            try:
                item, created = GameItem.objects.update_or_create(
                    game=game,
                    name=name,
                    defaults={'data': parsed}
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            except Exception as e:
                errors_processing.append(f"Error updating/creating item '{name}': {e}")

        if created_count > 0 or updated_count > 0:
            messages.success(request, f"Juego '{game.name}': {created_count} ítems creados, {updated_count} ítems actualizados.")
        if not errors_processing and created_count == 0 and updated_count == 0:
             messages.info(request, f"Juego '{game.name}': No se crearon ni actualizaron ítems. Los datos podrían estar ya sincronizados o no se encontraron ítems válidos.")
        for error_msg in errors_processing:
            messages.warning(request, f"Juego '{game.name}': {error_msg}")


    def sync_game_items_action(self, request, queryset):
        for game in queryset:
            raw_items = []
            source_type = None

            if game.json_file:
                source_type = "JSON file"
                try:
                    game.json_file.open('r')
                    data = json.load(game.json_file)
                    game.json_file.close()
                    if isinstance(data, list):
                        raw_items = data
                    elif isinstance(data, dict) and "results" in data and isinstance(data["results"], list): # Common pattern for paginated API-like JSON
                        raw_items = data["results"]
                    else: # Support a single JSON object as a list of one if not a list or expected dict structure
                        raw_items = [data] if isinstance(data, dict) else [] 
                    
                    if not raw_items and isinstance(data, dict) and not "results" in data:
                         messages.warning(request, f"El archivo JSON de '{game.name}' es un diccionario pero no contiene la clave 'results' con una lista de ítems. Se intentará procesar como un único ítem si es un diccionario.")


                except Exception as e:
                    messages.error(request, f"Error leyendo el archivo JSON para '{game.name}': {e}")
                    continue
            
            elif game.data_source_url:
                source_type = "API URL"
                list_url = game.data_source_url
                items_key_in_response = "results" # Default key for list of items if data_source_url is a single URL to a list

                try:
                    # Check if data_source_url is a JSON string континенující [list_url, items_key]
                    parsed_urls = json.loads(game.data_source_url)
                    if isinstance(parsed_urls, list) and len(parsed_urls) == 2:
                        list_url, items_key_in_response = parsed_urls
                except (json.JSONDecodeError, TypeError, ValueError):
                    # Not a JSON list of two elements, treat as single URL
                    pass

                self.message_user(request, f"Sincronizando '{game.name}' desde {source_type}: {list_url}", messages.INFO)

                try:
                    response = requests.get(list_url, timeout=30)
                    response.raise_for_status()
                    data_from_api = response.json()

                    # If data_source_url pointed to a list of objects with their own detail URLs
                    if items_key_in_response and isinstance(data_from_api, dict) and items_key_in_response in data_from_api:
                        summary_items = data_from_api.get(items_key_in_response, [])
                        if summary_items and isinstance(summary_items[0], dict) and "url" in summary_items[0]: # Heuristic for list-detail pattern
                            for item_summary in summary_items:
                                detail_url = item_summary.get("url")
                                if detail_url:
                                    try:
                                        detail_resp = requests.get(detail_url, timeout=10)
                                        detail_resp.raise_for_status()
                                        raw_items.append(detail_resp.json())
                                    except Exception as e_detail:
                                        messages.warning(request, f"Error obteniendo detalle desde {detail_url} para '{game.name}': {e_detail}")
                                else:
                                     raw_items.append(item_summary) # If no detail URL, use the summary itself
                        else: # It's a dictionary, but not the list-detail pattern, items are directly under the key
                            raw_items = summary_items
                    elif isinstance(data_from_api, list): # API returned a list directly
                        raw_items = data_from_api
                    else:
                        messages.warning(request, f"Respuesta inesperada de la API para '{game.name}'. Se esperaba una lista o un diccionario con clave '{items_key_in_response}'. Data: {str(data_from_api)[:200]}")
                        continue
                        
                except requests.exceptions.RequestException as e:
                    messages.error(request, f"Error obteniendo datos de la API para '{game.name}': {e}")
                    continue
                except json.JSONDecodeError as e:
                    messages.error(request, f"Error decodificando JSON de la API para '{game.name}': {e}")
                    continue

            else:
                messages.info(request, f"Juego '{game.name}' no tiene configurado ni archivo JSON ni URL de API para sincronizar.")
                continue
            
            if raw_items:
                self._process_items(request, game, raw_items)
            elif source_type: # Source was configured but no items found
                 messages.info(request, f"No se encontraron ítems para procesar desde {source_type} para el juego '{game.name}'.")


    sync_game_items_action.short_description = "Sincronizar ítems del juego (desde JSON o API)"

    actions = [sync_game_items_action]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        zip_file = form.cleaned_data.get('item_images_zip')
        if zip_file:
            game_slug = obj.slug
            base_item_image_dir = os.path.join(settings.MEDIA_ROOT, 'game_item_images')
            game_specific_image_dir = os.path.join(base_item_image_dir, game_slug)
            
            os.makedirs(game_specific_image_dir, exist_ok=True)

            try:
                with zipfile.ZipFile(zip_file, 'r') as zf:
                    processed_files = 0
                    errors = []
                    
                    for member_name in zf.namelist():
                        if member_name.endswith('/'):
                            continue
                        
                        original_filename = os.path.basename(member_name)
                        item_id_str, ext = os.path.splitext(original_filename)

                        if ext.lower() != '.png':
                            errors.append(f"Archivo '{original_filename}' no es .png, omitido.")
                            continue

                        try:
                            json_id_as_int = int(item_id_str)
                        except ValueError:
                            errors.append(f"El ID '{item_id_str}' (del archivo '{original_filename}') no es un entero válido y la imagen fue omitida. Solo se procesarán archivos con nombres de ID numéricos (ej: '1.png').")
                            continue
                        
                        target_path = os.path.join(game_specific_image_dir, original_filename)
                        
                        with open(target_path, 'wb') as f_out:
                            f_out.write(zf.read(member_name))
                        processed_files += 1
                    
                    if processed_files > 0:
                        messages.success(request, f"{processed_files} imágenes de ítems procesadas correctamente para '{obj.name}'.")
                    if errors:
                        for error_msg in errors:
                            messages.warning(request, error_msg)
                    if processed_files == 0 and not errors and zip_file:
                         messages.info(request, f"No se procesaron imágenes del ZIP. Asegúrate que los nombres sean 'ID_ITEM.png' y los ítems existan.")


            except zipfile.BadZipFile:
                messages.error(request, "El archivo subido no es un ZIP válido.")
            except Exception as e:
                messages.error(request, f"Ocurrió un error inesperado procesando el archivo ZIP: {e}")
        

@admin.register(GameItem)
class GameItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'game')
    list_filter = ('game',)
    search_fields = ('name',)


@admin.register(ScoringRule)
class ScoringRuleAdmin(admin.ModelAdmin):
    list_display  = ("game", "attempt_no", "points")
    list_filter   = ("game",)
    ordering      = ("game", "attempt_no")

