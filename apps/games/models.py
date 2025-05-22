from django.contrib.auth.models import User
from django.utils import timezone
from datetime import time, timedelta
from django.db.models import JSONField
from django.conf import settings
from django.db import models

class Game(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, help_text="URL del juego (ej: 'one-piece')")
    description = models.TextField(blank=True)
    icon_image = models.ImageField(upload_to='game_icons/', blank=True, null=True)
    background_image = models.ImageField(upload_to='game_background/', blank=True, null=True)
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


class DailyTarget(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    target = models.ForeignKey(GameItem, on_delete=models.CASCADE)
    date = models.DateField()

    class Meta:
        unique_together = (("game", "date"),)

    @classmethod
    def get_current(cls, game):
        now = timezone.now()
        target_date = now.date()
        return cls.objects.filter(game=game, date=target_date).select_related("target").first()

class GameResult(models.Model):
    user         = models.ForeignKey(User, on_delete=models.CASCADE)
    game         = models.ForeignKey(Game, on_delete=models.CASCADE)
    daily_target = models.ForeignKey(
        DailyTarget,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    attempts     = models.PositiveIntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'daily_target')



class GameAttempt(models.Model):
    user         = models.ForeignKey(User, on_delete=models.CASCADE)
    game         = models.ForeignKey(Game, on_delete=models.CASCADE)
    daily_target = models.ForeignKey(DailyTarget, on_delete=models.CASCADE)
    guess        = models.ForeignKey(GameItem, on_delete=models.CASCADE)
    is_correct   = models.BooleanField()
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['attempted_at']
