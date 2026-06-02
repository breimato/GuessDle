from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.services.wallet.score_service import ScoreService
from apps.games.models import RoscoJackpotWinner, RoscoWeeklyPot, WeeklyRosco


class WeeklyPotService:
    def __init__(self, weekly_rosco: WeeklyRosco):
        self.weekly_rosco = weekly_rosco

    @staticmethod
    def weekly_contribution_amount() -> float:
        return float(getattr(settings, "ROSCO_WEEKLY_POT_CONTRIBUTION", 1000))

    def initialize_pot(self) -> RoscoWeeklyPot:
        previous = (
            WeeklyRosco.objects.filter(
                game=self.weekly_rosco.game,
                mode=self.weekly_rosco.mode,
                is_team=self.weekly_rosco.is_team,
                week_start__lt=self.weekly_rosco.week_start,
            )
            .select_related("pot")
            .order_by("-week_start")
            .first()
        )
        rollover = 0.0
        if previous and hasattr(previous, "pot") and not previous.pot.settled:
            rollover = previous.pot.pot_amount
            previous.pot.settled = True
            previous.pot.settled_at = timezone.now()
            previous.pot.save(update_fields=["settled", "settled_at"])

        contribution = self.weekly_contribution_amount()
        pot_amount = rollover + contribution
        return RoscoWeeklyPot.objects.create(
            weekly_rosco=self.weekly_rosco,
            pot_amount=pot_amount,
            weekly_contribution=contribution,
            rollover_amount=rollover,
        )

    def get_pot(self) -> RoscoWeeklyPot:
        pot, _ = RoscoWeeklyPot.objects.get_or_create(
            weekly_rosco=self.weekly_rosco,
            defaults={
                "pot_amount": self.weekly_contribution_amount(),
                "weekly_contribution": self.weekly_contribution_amount(),
            },
        )
        return pot

    @transaction.atomic
    def register_perfect_winner(self, user, session) -> RoscoJackpotWinner:
        pot = self.get_pot()
        winner, created = RoscoJackpotWinner.objects.get_or_create(
            weekly_rosco=self.weekly_rosco,
            user=user,
            defaults={"session": session, "share_amount": 0},
        )
        if not created and winner.session_id != session.id:
            winner.session = session
            winner.save(update_fields=["session"])
        return winner

    @transaction.atomic
    def settle_pot(self) -> dict:
        pot = self.get_pot()
        if pot.settled:
            return {"settled": True, "winners": 0, "share_amount": 0}

        winners = list(
            RoscoJackpotWinner.objects.filter(weekly_rosco=self.weekly_rosco).select_related("user")
        )
        if not winners:
            pot.settled = True
            pot.settled_at = timezone.now()
            pot.save(update_fields=["settled", "settled_at"])
            return {"settled": True, "winners": 0, "share_amount": 0, "rolled_over": pot.pot_amount}

        share_amount = pot.pot_amount / len(winners)
        mode = self.weekly_rosco.mode
        for winner in winners:
            score_service = ScoreService(winner.user, self.weekly_rosco.game, mode=mode)
            score_service.score_obj.elo += share_amount
            score_service.score_obj.save(update_fields=["elo"])
            winner.share_amount = share_amount
            winner.save(update_fields=["share_amount"])

        pot.settled = True
        pot.settled_at = timezone.now()
        pot.save(update_fields=["settled", "settled_at"])
        return {
            "settled": True,
            "winners": len(winners),
            "share_amount": share_amount,
            "pot_amount": pot.pot_amount,
        }
