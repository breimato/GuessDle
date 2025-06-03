from django.contrib import admin
from .models import Game, GameItem, ScoringRule
from django import forms
from django.conf import settings
from django.contrib import messages
import zipfile
import os

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
            'fields': ('data_source_url', 'field_mapping', 'defaults', 'attributes', 'numeric_fields', 'audio_file')
        }),
        ('Subida Masiva de Imágenes de Ítems', {
            'fields': ('item_images_zip',)
        })
    )

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

