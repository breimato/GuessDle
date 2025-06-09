from django.contrib import admin
from .models import Game, GameItem, ScoringRule
from .models import GameAttempt, DailyTarget, ExtraDailyPlay, PlaySession
from apps.accounts.models import Challenge
from django import forms
from django.conf import settings
from django.contrib import messages
import zipfile
import os
import json
import requests
from apps.common.utils import extract_items_and_modes
from .models import GameMode, GameItemModeData


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
    'fields': (
        'data_source_url',
        'json_file',
        'field_mapping',
        'defaults',
        'attributes',
        'grouped_attributes',  # Añadido aquí
        'numeric_fields',
        'audio_file'
    )
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
            name_field_in_mapping = None
            for k, v in game.field_mapping.items():
                if k.upper() == 'NAME' or k.upper() == 'NOMBRE':
                    name_field_in_mapping = v
                    break

            if name_field_in_mapping:
                name = deep_get(raw, name_field_in_mapping)
            else:
                name = raw.get("name") or raw.get("nombre") or raw.get("NAME") or raw.get("NOMBRE")

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

                # ------ Soporte para overrides de modos -------
                if "modes" in raw:
                    for mode_slug, mode_data in raw["modes"].items():
                        try:
                            mode = GameMode.objects.get(game=game, slug=mode_slug)
                            GameItemModeData.objects.update_or_create(
                                item=item,
                                mode=mode,
                                defaults={"extra": mode_data}
                            )
                        except GameMode.DoesNotExist:
                            errors_processing.append(
                                f"Modo '{mode_slug}' no existe para el juego '{game.name}' (debería haberse creado antes).")
            except Exception as e:
                errors_processing.append(f"Error updating/creating item '{name}': {e}")

        if created_count > 0 or updated_count > 0:
            messages.success(request,
                             f"Juego '{game.name}': {created_count} ítems creados, {updated_count} ítems actualizados.")
        if not errors_processing and created_count == 0 and updated_count == 0:
            messages.info(request,
                          f"Juego '{game.name}': No se crearon ni actualizaron ítems. Los datos podrían estar ya sincronizados o no se encontraron ítems válidos.")
        for error_msg in errors_processing:
            messages.warning(request, f"Juego '{game.name}': {error_msg}")

    def sync_game_items_action(self, request, queryset):
        for game in queryset:
            raw_items = []
            modes_cfg = {}
            source_type = None

            # ------ Lógica para JSON local ------
            if game.json_file:
                source_type = "JSON file"
                try:
                    game.json_file.open('r')
                    data = json.load(game.json_file)
                    game.json_file.close()
                    try:
                        raw_items, modes_cfg = extract_items_and_modes(data)
                    except KeyError as e:
                        messages.error(request,
                                       f"El archivo JSON de '{game.name}' no tiene la clave 'items' o no es una lista raíz. Error: {e}")
                        continue

                    # --- Crear/actualizar modos en la BD ---
                    if modes_cfg:
                        for slug, cfg in modes_cfg.items():
                            GameMode.objects.update_or_create(
                                game=game,
                                slug=slug,
                                defaults={
                                    "name": cfg.get("name", slug.title()),
                                    "description": cfg.get("description", ""),
                                    "config": cfg,
                                },
                            )
                except Exception as e:
                    messages.error(request, f"Error leyendo el archivo JSON para '{game.name}': {e}")
                    continue

            # ------ Lógica para API remota ------
            elif game.data_source_url:
                source_type = "API URL"
                list_url = game.data_source_url
                items_key_in_response = "results"

                try:
                    parsed_urls = json.loads(game.data_source_url)
                    if isinstance(parsed_urls, list) and len(parsed_urls) == 2:
                        list_url, items_key_in_response = parsed_urls
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

                self.message_user(request, f"Sincronizando '{game.name}' desde {source_type}: {list_url}",
                                  messages.INFO)

                try:
                    response = requests.get(list_url, timeout=30)
                    response.raise_for_status()
                    data_from_api = response.json()

                    if items_key_in_response and isinstance(data_from_api,
                                                            dict) and items_key_in_response in data_from_api:
                        summary_items = data_from_api.get(items_key_in_response, [])
                        if summary_items and isinstance(summary_items[0], dict) and "url" in summary_items[0]:
                            for item_summary in summary_items:
                                detail_url = item_summary.get("url")
                                if detail_url:
                                    try:
                                        detail_resp = requests.get(detail_url, timeout=10)
                                        detail_resp.raise_for_status()
                                        raw_items.append(detail_resp.json())
                                    except Exception as e_detail:
                                        messages.warning(request,
                                                         f"Error obteniendo detalle desde {detail_url} para '{game.name}': {e_detail}")
                                else:
                                    raw_items.append(item_summary)
                        else:
                            raw_items = summary_items
                    elif isinstance(data_from_api, list):
                        raw_items = data_from_api
                    else:
                        messages.warning(request,
                                         f"Respuesta inesperada de la API para '{game.name}'. Se esperaba una lista o un diccionario con clave '{items_key_in_response}'. Data: {str(data_from_api)[:200]}")
                        continue

                except requests.exceptions.RequestException as e:
                    messages.error(request, f"Error obteniendo datos de la API para '{game.name}': {e}")
                    continue
                except json.JSONDecodeError as e:
                    messages.error(request, f"Error decodificando JSON de la API para '{game.name}': {e}")
                    continue

            else:
                messages.info(request,
                              f"Juego '{game.name}' no tiene configurado ni archivo JSON ni URL de API para sincronizar.")
                continue

            if raw_items:
                self._process_items(request, game, raw_items)
            elif source_type:
                messages.info(request,
                              f"No se encontraron ítems para procesar desde {source_type} para el juego '{game.name}'.")

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
    list_display = ('name', 'game', 'deleted', 'deleted_at')
    list_filter = ('game', 'deleted')
    search_fields = ('name',)
    actions = ['soft_delete_items', 'restore_items']

    @admin.action(description="Marcar como eliminado (soft delete)")
    def soft_delete_items(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(deleted=True, deleted_at=timezone.now())
        self.message_user(request, f"{updated} ítems marcados como eliminados (soft delete).")

    @admin.action(description="Restaurar ítems eliminados")
    def restore_items(self, request, queryset):
        updated = queryset.update(deleted=False, deleted_at=None)
        self.message_user(request, f"{updated} ítems restaurados.")



@admin.register(ScoringRule)
class ScoringRuleAdmin(admin.ModelAdmin):
    list_display  = ("game", "attempt_no", "points")
    list_filter   = ("game",)
    ordering      = ("game", "attempt_no")


@admin.register(GameAttempt)
class GameAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'guess', 'is_correct', 'attempted_at', 'session')
    list_filter = ('game', 'is_correct')
    search_fields = ('user__username', 'guess__name')

@admin.register(DailyTarget)
class DailyTargetAdmin(admin.ModelAdmin):
    list_display = ('game', 'target', 'date', 'is_team')
    list_filter = ('game', 'is_team', 'date')
    search_fields = ('game__name', 'target__name')

@admin.register(ExtraDailyPlay)
class ExtraDailyPlayAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'target', 'created_at', 'bet_amount', 'completed')
    list_filter = ('game', 'completed')
    search_fields = ('user__username', 'target__name')

@admin.register(PlaySession)
class PlaySessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'session_type', 'reference_id', 'completed_at')
    list_filter = ('game', 'session_type')
    search_fields = ('user__username',)

@admin.register(GameMode)
class GameModeAdmin(admin.ModelAdmin):
    list_display = ('game', 'slug', 'name', 'description')

@admin.register(GameItemModeData)
class GameItemModeDataAdmin(admin.ModelAdmin):
    list_display = ('item', 'mode')
    search_fields = ('item__name', 'mode__slug')



