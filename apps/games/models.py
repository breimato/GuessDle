from django.contrib.auth.models import User
from django.utils import timezone
from datetime import time, timedelta
from django.db.models import JSONField
from django.conf import settings
from django.db import models
import os
from colorfield.fields import ColorField
from django.core.exceptions import ValidationError


def game_json_file_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/json_files/<game_slug>/<filename>
    return f'json_files/{instance.slug}/{filename}'

class Game(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, help_text="URL del juego (ej: 'one-piece')")
    description = models.TextField(blank=True)
    icon_image = models.ImageField(upload_to='game_icons/', blank=True, null=True)
    background_image = models.ImageField(upload_to='game_background/', blank=True, null=True)
    color = ColorField(default="#FF0000", format="hex")
    numeric_fields = JSONField(default=list, blank=True, help_text="Atributos que deben compararse como números")
    audio_file = models.FileField(upload_to='game_audios/', null=True, blank=True)

    # Configuración de API
    data_source_url = models.URLField(blank=True, null=True, help_text="URL de la API para sincronizar los datos")
    json_file = models.FileField(upload_to=game_json_file_path, blank=True, null=True, help_text="Archivo JSON local para los datos del juego.")
    field_mapping = models.JSONField(default=dict, help_text="Mapeo de campos: {'nombre': 'api_field'}")
    defaults = models.JSONField(default=dict, help_text="Valores por defecto para campos faltantes")
    attributes = models.JSONField(default=list, help_text="Lista de atributos que tiene cada ítem")
    grouped_attributes = models.JSONField(default=list, help_text='Grupos de atributos a comparar conjuntamente (ej: [["tipo_1", "tipo_2"]])')

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.data_source_url and self.json_file:
            raise ValidationError(
                {'data_source_url': "No puedes proporcionar una URL de API y un archivo JSON a la vez. Escoge solo uno.",
                 'json_file': "No puedes proporcionar una URL de API y un archivo JSON a la vez. Escoge solo uno."})
        if not self.data_source_url and not self.json_file:
            raise ValidationError(
                {'data_source_url': "Debes proporcionar una URL de API o un archivo JSON.",
                 'json_file': "Debes proporcionar una URL de API o un archivo JSON."})


class GameItem(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=255)
    data = models.JSONField(default=dict, help_text="Diccionario de atributos del ítem")
    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('game', 'name')  # Un nombre único por juego

    def __str__(self):
        return f"{self.name} ({self.game.slug})"

    def get_image_filename(self):
        # Ahora que sync_game_data asegura que el 'id' original está en self.data['id'],
        # podemos buscarlo directamente.
        image_identifier = None
        if isinstance(self.data, dict):
            image_identifier = self.data.get('id')
        
        if image_identifier is None:
            # Opcional: Podrías loguear aquí si un item no tiene el 'id' esperado en data
            # print(f"Advertencia: GameItem '{self.name}' (ID: {self.id}) no tiene la clave 'id' en su campo 'data' para la imagen.")
            return None
        
        return f"{str(image_identifier)}.png"

    def get_image_url(self):
        filename = self.get_image_filename()

        if not filename:
            return None

        path_parts = ['game_item_images', self.game.slug, filename]
        disk_path = os.path.join(settings.MEDIA_ROOT, *path_parts)

        if os.path.exists(disk_path):
            base_url = settings.MEDIA_URL
            if not base_url.endswith('/'):
                base_url += '/'
            return base_url + "/".join(path_parts)
        
        return None


class DailyTarget(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    target = models.ForeignKey(GameItem, on_delete=models.CASCADE)
    date = models.DateField()
    is_team = models.BooleanField(default=False, help_text="¿Es un target de equipo?")

    class Meta:
        unique_together = (("game", "date", "is_team"),)

    @classmethod
    def get_current(cls, game, user):
        now = timezone.localtime()
        target_date = now.date()
        if now.time() >= time(23, 0):
            target_date += timedelta(days=1)

        is_team = getattr(getattr(user, "profile", None), "is_team_account", False)

        return (
            cls.objects
            .filter(game=game, date=target_date, is_team=is_team)
            .select_related("target")
            .first()
        )


class GameAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    guess = models.ForeignKey(GameItem, on_delete=models.CASCADE)
    mode = models.ForeignKey('games.GameMode', on_delete=models.CASCADE, null=True)
    is_correct = models.BooleanField()
    attempted_at = models.DateTimeField(auto_now_add=True)
    session = models.ForeignKey(
        'games.PlaySession',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='attempts'
    )

    class Meta:
        ordering = ['attempted_at']


class ExtraDailyPlay(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    target = models.ForeignKey('games.GameItem', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    bet_amount = models.FloatField(default=0)
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'game', 'created_at')

    def __str__(self):
        return f"ExtraDailyPlay: {self.user.username} - {self.game.name} - {self.target.name}"


class PlaySessionType(models.TextChoices):
    DAILY     = "DAILY", "Daily"
    EXTRA     = "EXTRA", "Extra"
    CHALLENGE = "CHALLENGE", "Challenge"

class PlaySession(models.Model):
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="play_sessions")
    game         = models.ForeignKey('games.Game', on_delete=models.CASCADE, related_name="play_sessions")
    session_type = models.CharField(max_length=10, choices=PlaySessionType.choices)
    reference_id = models.PositiveIntegerField(null=True, blank=True, help_text="PK de DailyTarget / ExtraDailyPlay / Challenge")
    mode = models.ForeignKey('games.GameMode', on_delete=models.CASCADE, null=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'game', 'session_type', 'reference_id')
        indexes = [
            models.Index(fields=['game', 'session_type']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user} - {self.game} - {self.session_type}"


class ScoringRule(models.Model):
    """
    Define cuántos puntos se otorgan si aciertas en un intento N.
    Se puede crear una regla por juego; si `game` es NULL ⇒ regla global.

    Está en el panel de admin para que el admin pueda definir las reglas de puntuación
    """
    game       = models.ForeignKey('games.Game', null=True, blank=True,
                                   on_delete=models.CASCADE, related_name='scoring_rules')
    attempt_no = models.PositiveIntegerField(help_text="1 = primer intento, 2 = segundo...")
    points     = models.PositiveIntegerField()

    class Meta:
        unique_together = ('game', 'attempt_no')
        ordering = ('attempt_no',)

    def __str__(self):
        scope = self.game.slug if self.game else "GLOBAL"
        return f"{scope}: intento {self.attempt_no} → {self.points} pts"



# ——— NUEVOS MODELOS ————————————————————————————

class GameMode(models.Model):
    """
    Variante de un juego (“classic”, “emoji”, “trivia”…).
    Cada Game puede tener varios GameMode.
    """
    game        = models.ForeignKey('games.Game', on_delete=models.CASCADE, related_name='modes')
    slug        = models.SlugField()                          # 'classic', 'emoji', etc.
    name        = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    config      = models.JSONField(default=dict, blank=True)  # reglas propias (nº intentos, etc.)

    class Meta:
        unique_together = ('game', 'slug')                    # No repitas el mismo slug en un juego

    def __str__(self):
        return f'{self.game.slug} • {self.slug}'


class GameItemModeData(models.Model):
    """
    Datos específicos de UN ítem en UN modo (pistas, emojis, pixel-art, etc.).
    """
    item  = models.ForeignKey('games.GameItem', on_delete=models.CASCADE, related_name='mode_data')
    mode  = models.ForeignKey('games.GameMode', on_delete=models.CASCADE, related_name='item_data')
    extra = models.JSONField(default=dict, blank=True)        # ej.: {"emojis_by_turn": ["👦", …]}

    class Meta:
        unique_together = ('item', 'mode')

    def __str__(self):
        return f'{self.item.name} @ {self.mode.slug}'


class EmojiPlaySession(models.Model):
    session = models.OneToOneField('games.PlaySession', on_delete=models.CASCADE, related_name='emoji_data')
    emoji_set_index = models.IntegerField()

    class Meta:
        unique_together = ('session',)

    def __str__(self):
        return f"EmojiData: session={self.session_id}, set={self.emoji_set_index}"



