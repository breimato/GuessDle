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
    hint_reveal_columns = models.JSONField(
        default=list,
        blank=True,
        help_text='Orden de preferencia para pistas de columna. Ej: ["tipo_1", "tipo_2", "generacion"]',
    )

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

        attributes = set(self.attributes or [])
        invalid_hints = [col for col in (self.hint_reveal_columns or []) if col not in attributes]
        if invalid_hints:
            raise ValidationError({
                'hint_reveal_columns': (
                    f"Columnas no definidas en attributes: {', '.join(invalid_hints)}"
                ),
            })

    def has_modes(self) -> bool:
        return self.modes.filter(active=True).exists()


class GameModePlayType(models.TextChoices):
    WORDLE = "wordle", "Wordle"
    ROSCO = "rosco", "Rosco"


class GameMode(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="modes")
    slug = models.SlugField()
    label = models.CharField(max_length=50)
    sort_order = models.PositiveSmallIntegerField(default=0)
    play_type = models.CharField(
        max_length=10,
        choices=GameModePlayType.choices,
        default=GameModePlayType.WORDLE,
    )
    item_filter = models.JSONField(default=dict, blank=True)
    background_image = models.ImageField(
        upload_to="game_mode_background/", blank=True, null=True
    )
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("game", "slug")
        ordering = ("sort_order", "slug")

    def __str__(self):
        return f"{self.game.slug}:{self.slug}"

    def pool_description(self) -> str:
        if self.play_type == GameModePlayType.ROSCO:
            return (
                "Rosco semanal Pasapalabra para cuentas de equipo: disponible solo los sábados, "
                "27 letras, un intento por letra y bote de ELO acumulado."
            )
        filt = self.item_filter or {}
        if "generacion__lte" in filt:
            count = int(filt["generacion__lte"])
            if count == 1:
                return "Este modo incluye la 1.ª generación."
            return f"Este modo incluye las {count} primeras generaciones."
        if "generacion__gte" in filt:
            count = int(filt["generacion__gte"])
            return f"Este modo incluye desde la generación {count}."
        if not filt:
            return "Este modo incluye todas las generaciones."
        return "Este modo incluye un conjunto personalizado de personajes."

    @property
    def is_rosco(self) -> bool:
        return self.play_type == GameModePlayType.ROSCO


class RoscoQuestionType(models.TextChoices):
    STARTS_WITH = "starts_with", "Empieza por"
    CONTAINS = "contains", "Contiene la letra"


class RoscoQuestion(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="rosco_questions")
    letter = models.CharField(max_length=2)
    question_type = models.CharField(max_length=20, choices=RoscoQuestionType.choices)
    prompt = models.TextField()
    acceptable_answers = models.JSONField(default=list)
    category = models.CharField(max_length=50, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("letter", "id")
        indexes = [models.Index(fields=["game", "letter", "active"])]

    def __str__(self):
        return f"{self.game.slug} [{self.letter}] {self.prompt[:40]}"


class WeeklyRosco(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="weekly_roscos")
    mode = models.ForeignKey(GameMode, on_delete=models.CASCADE, related_name="weekly_roscos")
    week_start = models.DateField(help_text="Inicio del periodo de 7 días del rosco (desde el primer Pasapalabra)")
    is_team = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["game", "mode", "week_start", "is_team"],
                name="unique_weekly_rosco",
            ),
        ]
        ordering = ("-week_start",)

    def __str__(self):
        return f"{self.game.slug}/{self.mode.slug} semana {self.week_start}"


class WeeklyRoscoEntry(models.Model):
    weekly_rosco = models.ForeignKey(WeeklyRosco, on_delete=models.CASCADE, related_name="entries")
    letter = models.CharField(max_length=2)
    sort_order = models.PositiveSmallIntegerField()
    question = models.ForeignKey(RoscoQuestion, on_delete=models.PROTECT)
    prompt_snapshot = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["weekly_rosco", "letter"],
                name="unique_weekly_rosco_letter",
            ),
        ]
        ordering = ("sort_order",)

    def __str__(self):
        return f"{self.weekly_rosco_id} [{self.letter}]"


class RoscoWeeklyPot(models.Model):
    weekly_rosco = models.OneToOneField(
        WeeklyRosco, on_delete=models.CASCADE, related_name="pot"
    )
    pot_amount = models.FloatField(default=0)
    weekly_contribution = models.FloatField(default=0)
    rollover_amount = models.FloatField(default=0)
    settled = models.BooleanField(default=False)
    settled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Bote {self.weekly_rosco_id}: {self.pot_amount} ELO"


class RoscoJackpotWinner(models.Model):
    weekly_rosco = models.ForeignKey(
        WeeklyRosco, on_delete=models.CASCADE, related_name="jackpot_winners"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rosco_jackpots")
    session = models.ForeignKey("PlaySession", on_delete=models.CASCADE, related_name="rosco_jackpots")
    share_amount = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["weekly_rosco", "user"],
                name="unique_rosco_jackpot_winner_per_week",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.share_amount} ELO"


class RoscoLetterAttempt(models.Model):
    session = models.ForeignKey("PlaySession", on_delete=models.CASCADE, related_name="rosco_attempts")
    letter = models.CharField(max_length=2)
    answer_text = models.CharField(max_length=255, blank=True)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "letter"],
                name="unique_rosco_attempt_per_letter",
            ),
        ]
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.session_id} [{self.letter}] {'✓' if self.is_correct else '✗'}"


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
    mode = models.ForeignKey(GameMode, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["game", "date", "is_team"],
                condition=models.Q(mode__isnull=True),
                name="unique_daily_target_no_mode",
            ),
            models.UniqueConstraint(
                fields=["game", "date", "is_team", "mode"],
                condition=models.Q(mode__isnull=False),
                name="unique_daily_target_with_mode",
            ),
        ]

    @classmethod
    def get_current(cls, game, user, mode=None):
        now = timezone.localtime()
        target_date = now.date()
        if now.time() >= time(23, 0):
            target_date += timedelta(days=1)

        is_team = getattr(getattr(user, "profile", None), "is_team_account", False)

        queryset = cls.objects.filter(
            game=game,
            date=target_date,
            is_team=is_team,
        )
        if mode is None:
            queryset = queryset.filter(mode__isnull=True)
        else:
            queryset = queryset.filter(mode=mode)
        return queryset.select_related("target", "mode").first()


class GameAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    guess = models.ForeignKey(GameItem, on_delete=models.CASCADE)
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
    mode = models.ForeignKey(GameMode, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    bet_amount = models.FloatField(default=0)
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'game', 'created_at')

    def __str__(self):
        return f"ExtraDailyPlay: {self.user.username} - {self.game.name} - {self.target.name}"


class PlaySessionType(models.TextChoices):
    DAILY = "DAILY", "Daily"
    EXTRA = "EXTRA", "Extra"
    CHALLENGE = "CHALLENGE", "Challenge"
    ROSCO = "ROSCO", "Rosco"


class RoscoSessionStatus(models.TextChoices):
    IN_PROGRESS = "in_progress", "En curso"
    FAILED = "failed", "Fallida"
    COMPLETED = "completed", "Completada"
    WON_PERFECT = "won_perfect", "Victoria perfecta"
    SURRENDERED = "surrendered", "Rendida"


class PlaySession(models.Model):
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="play_sessions")
    game         = models.ForeignKey('games.Game', on_delete=models.CASCADE, related_name="play_sessions")
    mode         = models.ForeignKey(GameMode, on_delete=models.CASCADE, null=True, blank=True)
    session_type = models.CharField(max_length=10, choices=PlaySessionType.choices)
    reference_id = models.PositiveIntegerField(null=True, blank=True, help_text="PK de DailyTarget / ExtraDailyPlay / Challenge")
    revealed_hints = models.JSONField(
        default=list,
        blank=True,
        help_text='Pistas de columna usadas: [{"attribute": "tipo_1", "value": "Fuego", "at_attempt": 5}]',
    )
    surrendered = models.BooleanField(default=False)
    rosco_current_letter = models.CharField(max_length=2, blank=True, default="")
    rosco_status = models.CharField(
        max_length=20,
        choices=RoscoSessionStatus.choices,
        blank=True,
        default="",
    )
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
