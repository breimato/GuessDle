from django.contrib.auth.models import User
from apps.games.models import Game
from django.db import models

class GameElo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    elo = models.FloatField(default=1200)
    partidas = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'game')

    def __str__(self):
        return f"{self.user.username} - {self.game.slug}: {int(self.elo)}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    is_team_account = models.BooleanField(default=False)

    def __str__(self):
        return f"Perfil de {self.user.username}"