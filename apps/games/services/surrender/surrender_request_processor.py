from django.http import JsonResponse

from apps.games.services.play_session.context_builder import ContextBuilder

from .surrender_service import SurrenderService


class SurrenderRequestProcessor:
    def __init__(self, request, game):
        self.request = request
        self.game = game

    def process(self, *, daily_target=None, extra_play=None, challenge=None):
        play_context = ContextBuilder(
            self.request,
            self.game,
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        ).build()

        if not play_context["can_play"]:
            return JsonResponse({"error": "You cannot play anymore."}, status=403)

        try:
            surrender_result = SurrenderService(self.game, self.request.user).process(
                daily_target=daily_target,
                extra_play=extra_play,
                challenge=challenge,
            )
        except ValueError as error:
            return JsonResponse({"error": str(error)}, status=400)

        return self._build_json_response(surrender_result)

    def _build_json_response(self, surrender_result):
        response_data = {
            "surrendered": True,
            "target_name": surrender_result.target_name,
        }
        response_data.update(surrender_result.points_data)

        if not surrender_result.challenge_data:
            return JsonResponse(response_data)

        response_data["challenge"] = surrender_result.challenge_data
        return JsonResponse(response_data)
