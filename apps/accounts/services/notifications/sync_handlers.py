from dataclasses import dataclass, field

from django.template.loader import render_to_string

from apps.accounts.services.notifications.notification_types import NotificationType


@dataclass
class DashboardSyncState:
    inserts: list = field(default_factory=list)
    removes: list = field(default_factory=list)
    updates: list = field(default_factory=list)


class NotificationSyncHandler:

    notification_type = None

    def applies(self, notification) -> bool:
        return notification.type == self.notification_type

    def apply(self, notification, user, request, state: DashboardSyncState):
        raise NotImplementedError


class ChallengeReceivedSyncHandler(NotificationSyncHandler):
    notification_type = NotificationType.CHALLENGE_RECEIVED

    def apply(self, notification, user, request, state: DashboardSyncState):
        challenge = notification.challenge
        if not challenge:
            return

        state.inserts.append(
            {
                "panel": "pending",
                "challenge_id": challenge.id,
                "html": render_to_string(
                    "partials/pending_challenge_card.html",
                    {"challenge": challenge},
                    request=request,
                ),
            }
        )


class ChallengeAcceptedSyncHandler(NotificationSyncHandler):
    notification_type = NotificationType.CHALLENGE_ACCEPTED

    def apply(self, notification, user, request, state: DashboardSyncState):
        challenge = notification.challenge
        if not challenge:
            return

        state.removes.append(challenge.id)
        state.inserts.append(
            {
                "panel": "active",
                "challenge_id": challenge.id,
                "html": render_to_string(
                    "partials/active_challenge_card.html",
                    {"challenge": challenge, "user": user},
                    request=request,
                ),
            }
        )


class ChallengeRemovedSyncHandler(NotificationSyncHandler):
    notification_types = (
        NotificationType.CHALLENGE_REJECTED,
        NotificationType.CHALLENGE_CANCELLED,
    )

    def applies(self, notification) -> bool:
        return notification.type in self.notification_types

    def apply(self, notification, user, request, state: DashboardSyncState):
        challenge_id = notification.payload.get("challenge_id")
        if challenge_id:
            state.removes.append(challenge_id)


class RivalFinishedSyncHandler(NotificationSyncHandler):
    notification_type = NotificationType.RIVAL_FINISHED

    def apply(self, notification, user, request, state: DashboardSyncState):
        challenge = notification.challenge
        if not challenge:
            return

        state.updates.append(
            {
                "panel": "active",
                "challenge_id": challenge.id,
                "html": render_to_string(
                    "partials/active_challenge_card.html",
                    {"challenge": challenge, "user": user},
                    request=request,
                ),
            }
        )


class ChallengeOutcomeSyncHandler(NotificationSyncHandler):
    notification_types = (
        NotificationType.CHALLENGE_WIN,
        NotificationType.CHALLENGE_LOSS,
        NotificationType.CHALLENGE_TIE,
    )

    def applies(self, notification) -> bool:
        return notification.type in self.notification_types

    def apply(self, notification, user, request, state: DashboardSyncState):
        challenge_id = notification.payload.get("challenge_id")
        if challenge_id:
            state.removes.append(challenge_id)


SYNC_HANDLERS = [
    ChallengeReceivedSyncHandler(),
    ChallengeAcceptedSyncHandler(),
    ChallengeRemovedSyncHandler(),
    RivalFinishedSyncHandler(),
    ChallengeOutcomeSyncHandler(),
]


def apply_notification_sync(user, notifications, request) -> dict:
    state = DashboardSyncState()

    for notification in notifications:
        for handler in SYNC_HANDLERS:
            if handler.applies(notification):
                handler.apply(notification, user, request, state)
                break

    return {
        "inserts": state.inserts,
        "removes": list(dict.fromkeys(state.removes)),
        "updates": state.updates,
    }
