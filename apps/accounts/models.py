from django.contrib.auth.models import User
from django.db import models


class GameElo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey('games.Game', on_delete=models.CASCADE)  # referencia perezosa
    elo = models.FloatField(default=0)
    partidas = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'game')

    def __str__(self):
        return f"{self.user.username} - {self.game.slug}: {int(self.elo)}"


class Challenge(models.Model):
    challenger = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenges_sent')
    opponent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenges_received')
    game = models.ForeignKey('games.Game', on_delete=models.CASCADE)
    target = models.ForeignKey('games.GameItem', on_delete=models.CASCADE, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    winner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='won_challenges')
    elo_exchanged = models.BooleanField(default=False)
    challenger_attempts = models.PositiveIntegerField(null=True, blank=True)
    opponent_attempts = models.PositiveIntegerField(null=True, blank=True)
    points_assigned = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.challenger.username} vs {self.opponent.username}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    is_team_account = models.BooleanField(default=False)

    def __str__(self):
        return f"Perfil de {self.user.username}"
