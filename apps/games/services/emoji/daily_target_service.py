from django.utils import timezone

from apps.games.models import DailyTarget, EmojiClueSet, Game, GameMode, PlaySession, PlaySessionType
from apps.games.services.catalog.item_pool_service import ItemPoolService
from apps.games.services.daily.target_service import TargetService
from apps.games.services.emoji.clue_service import EmojiClueService


class EmojiDailyTargetService:
    def __init__(self, game: Game, user, mode: GameMode):
        self.game = game
        self.user = user
        self.mode = mode
        self.target_service = TargetService(game, user, mode=mode)

    @staticmethod
    def has_clue_bank(game: Game) -> bool:
        return EmojiClueSet.objects.filter(game=game, active=True).exists()

    def get_today_target(self) -> DailyTarget | None:
        return self.target_service.get_target_for_today()

    def target_has_clues(self, daily_target: DailyTarget) -> bool:
        return bool(EmojiClueService.get_clues(self.game, daily_target.target))

    def _pick_item_with_clues(self):
        return ItemPoolService(self.game, self.mode).pick_random_with_emoji_clues()

    def ensure_today_target(self) -> DailyTarget | None:
        existing = self.get_today_target()
        if existing:
            return existing

        item = self._pick_item_with_clues()
        if not item:
            return None

        return DailyTarget.objects.create(
            game=self.game,
            mode=self.mode,
            date=timezone.localdate(),
            is_team=self.target_service.is_team_account,
            target=item,
        )

    def _session_has_attempts(self, daily_target: DailyTarget) -> bool:
        session = PlaySession.objects.filter(
            user=self.user,
            game=self.game,
            session_type=PlaySessionType.DAILY,
            reference_id=daily_target.id,
        ).first()
        if not session:
            return False
        return session.attempts.exists()

    def repair_today_target_if_invalid(self, daily_target: DailyTarget) -> DailyTarget | None:
        if self.target_has_clues(daily_target):
            return daily_target
        if self._session_has_attempts(daily_target):
            return daily_target

        item = self._pick_item_with_clues()
        if not item:
            return daily_target

        daily_target.target = item
        daily_target.save(update_fields=["target"])
        return daily_target

    def resolve_playable_target(self) -> DailyTarget | None:
        if not self.has_clue_bank(self.game):
            return None

        daily_target = self.ensure_today_target()
        if not daily_target:
            return None

        daily_target = self.repair_today_target_if_invalid(daily_target)
        if not self.target_has_clues(daily_target):
            return None
        return daily_target
