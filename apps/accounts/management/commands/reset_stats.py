# apps/games/management/commands/reset_stats.py

from django.core.management.base import BaseCommand
from apps.accounts.models import GameElo
from apps.games.models import PlaySession, GameAttempt, ExtraDailyPlay, GameResult


class Command(BaseCommand):
    help = (
        "Elimina todos los registros de partidas jugadas y resetea puntos:\n"
        "  • Borra todas las GameResult (resultados históricos).\n"
        "  • Borra todos los GameAttempt (intentos de juego).\n"
        "  • Borra todas las PlaySession (sesiones de juego).\n"
        "  • Borra todas las ExtraDailyPlay (partidas extra).\n"
        "  • Pone a cero 'elo' y 'partidas' en GameElo."
    )

    def handle(self, *args, **options):
        # 1️⃣ Borrar todos los GameResult (resultados históricos)
        deleted_results = GameResult.objects.count()
        GameResult.objects.all().delete()
        self.stdout.write(f"🗑 Eliminados {deleted_results} registros de GameResult.")

        # 2️⃣ Borrar todos los GameAttempt (intentos)
        deleted_attempts = GameAttempt.objects.count()
        GameAttempt.objects.all().delete()
        self.stdout.write(f"🗑 Eliminados {deleted_attempts} registros de GameAttempt.")

        # 3️⃣ Borrar todas las PlaySession
        deleted_sessions = PlaySession.objects.count()
        PlaySession.objects.all().delete()
        self.stdout.write(f"🗑 Eliminadas {deleted_sessions} PlaySession.")

        # 4️⃣ Borrar todas las ExtraDailyPlay (partidas extra)
        deleted_extra = ExtraDailyPlay.objects.count()
        ExtraDailyPlay.objects.all().delete()
        self.stdout.write(f"🗑 Eliminadas {deleted_extra} partidas ExtraDailyPlay.")

        # 5️⃣ Resetear los campos 'elo' y 'partidas' en GameElo
        updated_elos = GameElo.objects.update(elo=0.0, partidas=0)
        self.stdout.write(self.style.SUCCESS(
            f"♻️ Reseteados {updated_elos} registros de GameElo (elo y partidas a 0)."
        ))
