from apps.games.models import Game, ProximityPrompt


class ProximityPromptImportError(Exception):
    pass


def validate_proximity_prompt_payload(payload: list, *, source: str = "JSON") -> None:
    if not isinstance(payload, list) or not payload:
        raise ProximityPromptImportError(f"{source}: se esperaba una lista no vacía.")
    for index, entry in enumerate(payload, start=1):
        if not isinstance(entry, dict):
            raise ProximityPromptImportError(f"{source}: entrada #{index} inválida.")
        if not str(entry.get("prompt", "")).strip():
            raise ProximityPromptImportError(f"{source}: entrada #{index} sin prompt.")
        try:
            int(entry["answer_chapter"])
        except (KeyError, TypeError, ValueError) as error:
            raise ProximityPromptImportError(
                f"{source}: entrada #{index} sin answer_chapter válido."
            ) from error
        if entry.get("answer_episode") is not None:
            try:
                int(entry["answer_episode"])
            except (TypeError, ValueError) as error:
                raise ProximityPromptImportError(
                    f"{source}: entrada #{index} con answer_episode inválido."
                ) from error


def import_proximity_prompts(game: Game, payload: list, *, source: str = "JSON") -> int:
    validate_proximity_prompt_payload(payload, source=source)
    upserted = 0
    for entry in payload:
        prompt_text = str(entry["prompt"]).strip()
        answer_value = int(entry["answer_chapter"])
        answer_episode = entry.get("answer_episode")
        answer_episode = int(answer_episode) if answer_episode is not None else None
        arcs = [str(arc).strip() for arc in (entry.get("arcs") or []) if str(arc).strip()]
        kind = str(entry.get("kind") or "event").strip()
        active = entry.get("active", True)

        existing = ProximityPrompt.objects.filter(
            game=game, prompt_text=prompt_text
        ).first()
        if existing:
            existing.answer_value = answer_value
            existing.answer_episode = answer_episode
            existing.arcs = arcs
            existing.kind = kind
            existing.active = active
            existing.save(
                update_fields=["answer_value", "answer_episode", "arcs", "kind", "active"]
            )
        else:
            ProximityPrompt.objects.create(
                game=game,
                prompt_text=prompt_text,
                answer_value=answer_value,
                answer_episode=answer_episode,
                arcs=arcs,
                kind=kind,
                active=active,
            )
        upserted += 1
    return upserted
