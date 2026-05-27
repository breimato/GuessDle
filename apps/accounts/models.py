from django.contrib.auth.models import User
from django.db import models


class GameElo(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey('games.Game', on_delete=models.CASCADE)
    mode = models.ForeignKey('games.GameMode', on_delete=models.CASCADE, null=True, blank=True)
    elo = models.FloatField(default=0)
    partidas = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'game'],
                condition=models.Q(mode__isnull=True),
                name='unique_game_elo_no_mode',
            ),
            models.UniqueConstraint(
                fields=['user', 'game', 'mode'],
                condition=models.Q(mode__isnull=False),
                name='unique_game_elo_with_mode',
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.game.slug}: {int(self.elo)}"


class Challenge(models.Model):

    challenger = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenges_sent')
    opponent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenges_received')
    game = models.ForeignKey('games.Game', on_delete=models.CASCADE)
    mode = models.ForeignKey('games.GameMode', on_delete=models.CASCADE, null=True, blank=True)
    target = models.ForeignKey('games.GameItem', on_delete=models.CASCADE, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    winner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='won_challenges')
    elo_exchanged = models.BooleanField(default=False)
    challenger_attempts = models.PositiveIntegerField(null=True, blank=True)
    opponent_attempts = models.PositiveIntegerField(null=True, blank=True)
    points_assigned = models.BooleanField(default=False)
    winner_notified = models.BooleanField(default=False)
    loser_notified = models.BooleanField(default=False)
    stake_points = models.FloatField(default=0)
    stake_settled = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.challenger.username} vs {self.opponent.username}"


class Notification(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=32)
    payload = models.JSONField(default=dict)
    challenge = models.ForeignKey(
        Challenge,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "read_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} — {self.type}"


class UserProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    is_team_account = models.BooleanField(default=False)

    def __str__(self):
        return f"Perfil de {self.user.username}"
