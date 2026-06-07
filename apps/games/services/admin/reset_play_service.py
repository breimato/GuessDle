from django.db import transaction

from apps.games.models import (
    GameAttempt,
    PlaySession,
    PlaySessionType,
    ProximityAttempt,
    ProximityDailyAssignment,
    SilhouetteDailyAssignment,
)


@transaction.atomic
def reset_play_session(session: PlaySession) -> int:
    proximity_deleted, _ = ProximityAttempt.objects.filter(session=session).delete()
    attempts_deleted, _ = GameAttempt.objects.filter(session=session).delete()
    session.surrendered = False
    session.revealed_hints = []
    session.proximity_filter = {}
    session.proximity_first_distance = None
    session.proximity_score_locked = None
    session.proximity_completed = False
    session.proximity_started_at = None
    session.proximity_timed_out = False
    session.emoji_clues_revealed = 1
    session.rosco_current_letter = ""
    session.rosco_status = ""
    session.save()
    return attempts_deleted + proximity_deleted


@transaction.atomic
def delete_assignment_sessions(*, session_type: str, assignment_ids: list[int]) -> int:
    deleted, _ = PlaySession.objects.filter(
        session_type=session_type,
        reference_id__in=assignment_ids,
    ).delete()
    return deleted


@transaction.atomic
def reset_silhouette_assignment(
    assignment: SilhouetteDailyAssignment,
    *,
    delete_assignment: bool = False,
) -> None:
    sessions = PlaySession.objects.filter(
        session_type=PlaySessionType.SILHOUETTE,
        reference_id=assignment.id,
    )
    for session in sessions:
        reset_play_session(session)
    if delete_assignment:
        assignment.delete()


@transaction.atomic
def reset_proximity_assignment(
    assignment: ProximityDailyAssignment,
    *,
    delete_assignment: bool = False,
) -> None:
    sessions = PlaySession.objects.filter(
        session_type=PlaySessionType.PROXIMITY,
        reference_id=assignment.id,
    )
    for session in sessions:
        reset_play_session(session)
    if delete_assignment:
        assignment.delete()


@transaction.atomic
def delete_silhouette_assignments(queryset) -> int:
    assignment_ids = list(queryset.values_list("pk", flat=True))
    delete_assignment_sessions(
        session_type=PlaySessionType.SILHOUETTE,
        assignment_ids=assignment_ids,
    )
    deleted, _ = queryset.delete()
    return deleted


@transaction.atomic
def delete_proximity_assignments(queryset) -> int:
    assignment_ids = list(queryset.values_list("pk", flat=True))
    delete_assignment_sessions(
        session_type=PlaySessionType.PROXIMITY,
        assignment_ids=assignment_ids,
    )
    deleted, _ = queryset.delete()
    return deleted
