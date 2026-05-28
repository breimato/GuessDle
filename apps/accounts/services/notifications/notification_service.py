from django.db import models
from django.utils import timezone

from apps.accounts.services.notifications.notification_types import NotificationType
from apps.accounts.services.notifications.sync_handlers import apply_notification_sync
from apps.accounts.models import Challenge, Notification


class NotificationService:

    @staticmethod
    def challenge_payload(challenge, opponent_username=None, points_delta=None):
        rival = opponent_username
        if rival is None:
            rival = (
                challenge.opponent.username
                if challenge.challenger_id != challenge.opponent_id
                else challenge.challenger.username
            )
        payload = {
            "challenge_id": challenge.id,
            "game_name": challenge.game.name,
            "opponent_username": rival,
        }
        if points_delta is not None:
            payload["points_delta"] = points_delta
        return payload

    @staticmethod
    def create(user, notification_type, payload, challenge=None):
        if challenge is not None:
            already_pending = Notification.objects.filter(
                user=user,
                type=notification_type,
                challenge=challenge,
                read_at__isnull=True,
            ).exists()
            if already_pending:
                return None

        return Notification.objects.create(
            user=user,
            type=notification_type,
            payload=payload,
            challenge=challenge,
        )

    @staticmethod
    def notify_challenge_received(challenge):
        payload = NotificationService.challenge_payload(
            challenge,
            opponent_username=challenge.challenger.username,
        )
        NotificationService.create(
            challenge.opponent,
            NotificationType.CHALLENGE_RECEIVED,
            payload,
            challenge,
        )

    @staticmethod
    def notify_challenge_accepted(challenge):
        payload = NotificationService.challenge_payload(
            challenge,
            opponent_username=challenge.opponent.username,
        )
        NotificationService.create(
            challenge.challenger,
            NotificationType.CHALLENGE_ACCEPTED,
            payload,
            challenge,
        )

    @staticmethod
    def notify_challenge_rejected(challenge):
        payload = NotificationService.challenge_payload(
            challenge,
            opponent_username=challenge.opponent.username,
        )
        NotificationService.create(
            challenge.challenger,
            NotificationType.CHALLENGE_REJECTED,
            payload,
        )

    @staticmethod
    def notify_challenge_cancelled(challenge):
        payload = NotificationService.challenge_payload(
            challenge,
            opponent_username=challenge.challenger.username,
        )
        NotificationService.create(
            challenge.opponent,
            NotificationType.CHALLENGE_CANCELLED,
            payload,
        )

    @staticmethod
    def notify_rival_finished(challenge, finished_user):
        recipient = (
            challenge.opponent
            if finished_user == challenge.challenger
            else challenge.challenger
        )
        recipient_has_finished = (
            challenge.opponent_attempts is not None
            if recipient == challenge.opponent
            else challenge.challenger_attempts is not None
        )
        if recipient_has_finished:
            return

        payload = NotificationService.challenge_payload(
            challenge,
            opponent_username=finished_user.username,
        )
        NotificationService.create(
            recipient,
            NotificationType.RIVAL_FINISHED,
            payload,
            challenge,
        )

    @staticmethod
    def notify_challenge_outcome(challenge, acting_user):
        if challenge.winner is None:
            NotificationService._notify_tie(challenge, acting_user)
            return

        winner = challenge.winner
        stake_points = float(challenge.stake_points or 0)
        loser = (
            challenge.challenger
            if winner == challenge.opponent
            else challenge.opponent
        )

        if acting_user != winner:
            win_payload = NotificationService.challenge_payload(
                challenge,
                opponent_username=loser.username,
                points_delta=stake_points,
            )
            NotificationService.create(
                winner,
                NotificationType.CHALLENGE_WIN,
                win_payload,
                challenge,
            )

        if acting_user != loser:
            loss_payload = NotificationService.challenge_payload(
                challenge,
                opponent_username=winner.username,
                points_delta=-stake_points,
            )
            NotificationService.create(
                loser,
                NotificationType.CHALLENGE_LOSS,
                loss_payload,
                challenge,
            )

    @staticmethod
    def _notify_tie(challenge, acting_user):
        stake_points = float(challenge.stake_points or 0)
        for participant in (challenge.challenger, challenge.opponent):
            if participant == acting_user:
                continue
            rival = (
                challenge.opponent
                if participant == challenge.challenger
                else challenge.challenger
            )
            tie_payload = NotificationService.challenge_payload(
                challenge,
                opponent_username=rival.username,
                points_delta=-stake_points,
            )
            NotificationService.create(
                participant,
                NotificationType.CHALLENGE_TIE,
                tie_payload,
                challenge,
            )

    @staticmethod
    def fetch_unread(user):
        return Notification.objects.filter(
            user=user,
            read_at__isnull=True,
        ).select_related("challenge__game", "challenge__challenger", "challenge__opponent").order_by("created_at")

    @staticmethod
    def serialize(notification):
        return {
            "id": notification.id,
            "type": notification.type,
            "payload": notification.payload,
        }

    @staticmethod
    def ack(user, notification_ids):
        if not notification_ids:
            return 0
        return Notification.objects.filter(
            user=user,
            id__in=notification_ids,
            read_at__isnull=True,
        ).update(read_at=timezone.now())

    @staticmethod
    def build_dashboard_sync(user, notifications, request):
        return apply_notification_sync(user, notifications, request)

    @staticmethod
    def migrate_legacy_unread(user):
        won = Challenge.objects.filter(
            completed=True,
            winner=user,
            winner_notified=False,
        ).select_related("challenger", "opponent", "game")

        for challenge in won:
            rival = (
                challenge.opponent
                if challenge.challenger == user
                else challenge.challenger
            )
            NotificationService.create(
                user,
                NotificationType.CHALLENGE_WIN,
                NotificationService.challenge_payload(
                    challenge,
                    rival.username,
                    points_delta=float(challenge.stake_points or 0),
                ),
                challenge,
            )
            challenge.winner_notified = True
            challenge.save(update_fields=["winner_notified"])

        lost = Challenge.objects.filter(
            completed=True,
            loser_notified=False,
        ).filter(
            models.Q(challenger=user) | models.Q(opponent=user)
        ).exclude(winner=user).exclude(winner__isnull=True).select_related("winner", "game")

        for challenge in lost:
            NotificationService.create(
                user,
                NotificationType.CHALLENGE_LOSS,
                NotificationService.challenge_payload(
                    challenge,
                    challenge.winner.username,
                    points_delta=-float(challenge.stake_points or 0),
                ),
                challenge,
            )
            challenge.loser_notified = True
            challenge.save(update_fields=["loser_notified"])

        ties = Challenge.objects.filter(
            completed=True,
            winner__isnull=True,
        ).filter(
            (models.Q(challenger=user) & models.Q(winner_notified=False))
            | (models.Q(opponent=user) & models.Q(loser_notified=False))
        ).select_related("challenger", "opponent", "game")

        for challenge in ties:
            rival = (
                challenge.opponent
                if challenge.challenger == user
                else challenge.challenger
            )
            NotificationService.create(
                user,
                NotificationType.CHALLENGE_TIE,
                NotificationService.challenge_payload(
                    challenge,
                    rival.username,
                    points_delta=-float(challenge.stake_points or 0),
                ),
                challenge,
            )
            if challenge.challenger == user:
                challenge.winner_notified = True
                challenge.save(update_fields=["winner_notified"])
            else:
                challenge.loser_notified = True
                challenge.save(update_fields=["loser_notified"])
