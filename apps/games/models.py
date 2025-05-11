from django.db.models import JSONField

from django.db import models

class Game(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, help_text="URL del juego (ej: 'one-piece')")
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='game_icons/', blank=True, null=True)
    numeric_fields = JSONField(default=list, blank=True, help_text="Atributos que deben compararse como números")



    # Configuración de API
    data_source_url = models.URLField(blank=True, null=True, help_text="URL de la API para sincronizar los datos")
    field_mapping = models.JSONField(default=dict, help_text="Mapeo de campos: {'nombre': 'api_field'}")
    defaults = models.JSONField(default=dict, help_text="Valores por defecto para campos faltantes")
    attributes = models.JSONField(default=list, help_text="Lista de atributos que tiene cada ítem")

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class GameItem(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=255)
    data = models.JSONField(default=dict, help_text="Diccionario de atributos del ítem")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('game', 'name')  # Un nombre único por juego

    def __str__(self):
        return f"{self.name} ({self.game.slug})"
