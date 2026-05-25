from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone

from apps.accounts.models import Challenge, Notification


class NotificationType:
    CHALLENGE_RECEIVED = "challenge_received"
    CHALLENGE_ACCEPTED = "challenge_accepted"
    CHALLENGE_REJECTED = "challenge_rejected"
    CHALLENGE_CANCELLED = "challenge_cancelled"
    CHALLENGE_WIN = "challenge_win"
    CHALLENGE_LOSS = "challenge_loss"
    CHALLENGE_TIE = "challenge_tie"
    RIVAL_FINISHED = "rival_finished"


class NotificationService:

    @staticmethod
    def challenge_payload(challenge, opponent_username=None):
        rival = opponent_username
        if rival is None:
            rival = (
                challenge.opponent.username
                if challenge.challenger_id != challenge.opponent_id
                else challenge.challenger.username
            )
        return {
            "challenge_id": challenge.id,
            "game_name": challenge.game.name,
            "opponent_username": rival,
        }

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
        loser = (
            challenge.challenger
            if winner == challenge.opponent
            else challenge.opponent
        )

        if acting_user != winner:
            win_payload = NotificationService.challenge_payload(
                challenge,
                opponent_username=loser.username,
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
            )
            NotificationService.create(
                loser,
                NotificationType.CHALLENGE_LOSS,
                loss_payload,
                challenge,
            )

    @staticmethod
    def _notify_tie(challenge, acting_user):
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
        inserts = []
        removes = []
        updates = []

        for notification in notifications:
            challenge = notification.challenge
            challenge_id = notification.payload.get("challenge_id")

            if notification.type == NotificationType.CHALLENGE_RECEIVED and challenge:
                inserts.append({
                    "panel": "pending",
                    "challenge_id": challenge.id,
                    "html": render_to_string(
                        "partials/pending_challenge_card.html",
                        {"challenge": challenge},
                        request=request,
                    ),
                })

            elif notification.type == NotificationType.CHALLENGE_ACCEPTED and challenge:
                removes.append(challenge.id)
                inserts.append({
                    "panel": "active",
                    "challenge_id": challenge.id,
                    "html": render_to_string(
                        "partials/active_challenge_card.html",
                        {"challenge": challenge, "user": user},
                        request=request,
                    ),
                })

            elif notification.type in (
                NotificationType.CHALLENGE_REJECTED,
                NotificationType.CHALLENGE_CANCELLED,
            ):
                if challenge_id:
                    removes.append(challenge_id)

            elif notification.type == NotificationType.RIVAL_FINISHED and challenge:
                updates.append({
                    "panel": "active",
                    "challenge_id": challenge.id,
                    "html": render_to_string(
                        "partials/active_challenge_card.html",
                        {"challenge": challenge, "user": user},
                        request=request,
                    ),
                })

            elif notification.type in (
                NotificationType.CHALLENGE_WIN,
                NotificationType.CHALLENGE_LOSS,
                NotificationType.CHALLENGE_TIE,
            ):
                if challenge_id:
                    removes.append(challenge_id)

        return {
            "inserts": inserts,
            "removes": list(dict.fromkeys(removes)),
            "updates": updates,
        }

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
                NotificationService.challenge_payload(challenge, rival.username),
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
                NotificationService.challenge_payload(challenge, challenge.winner.username),
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
                NotificationService.challenge_payload(challenge, rival.username),
                challenge,
            )
            if challenge.challenger == user:
                challenge.winner_notified = True
                challenge.save(update_fields=["winner_notified"])
            else:
                challenge.loser_notified = True
                challenge.save(update_fields=["loser_notified"])
