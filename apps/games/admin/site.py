from django.contrib import admin

GAMES_MODEL_GROUPS = [
    ("Core", ["Game", "GameItem", "ScoringRule", "ArcCatalog"]),
    ("Wordle", ["DailyTarget", "ExtraDailyPlay"]),
    ("Silueta", ["SilhouetteDailyAssignment"]),
    ("Proximidad", ["ProximityPrompt", "ProximityDailyAssignment", "ProximityAttempt"]),
    ("Emoji", ["EmojiClueSet"]),
    (
        "Pasapalabra",
        [
            "RoscoQuestion",
            "WeeklyRosco",
            "RoscoWeeklyPot",
            "RoscoLetterAttempt",
            "RoscoJackpotWinner",
        ],
    ),
    ("Sesiones", ["PlaySession", "GameAttempt"]),
]


class GuessDleAdminSite(admin.AdminSite):
    site_header = "GuessDle Admin"
    site_title = "GuessDle Admin"
    index_title = "Administración"

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        games_app = next((app for app in app_list if app["app_label"] == "games"), None)
        if games_app is None:
            return app_list

        models_by_name = {model["object_name"]: model for model in games_app["models"]}
        grouped_apps = []
        for section_name, model_names in GAMES_MODEL_GROUPS:
            section_models = [
                models_by_name[model_name]
                for model_name in model_names
                if model_name in models_by_name
            ]
            if not section_models:
                continue
            grouped_apps.append(
                {
                    "name": section_name,
                    "app_label": f"games_{section_name.lower()}",
                    "app_url": games_app["app_url"],
                    "has_module_perms": games_app["has_module_perms"],
                    "models": section_models,
                }
            )

        remaining_apps = [app for app in app_list if app["app_label"] != "games"]
        return grouped_apps + remaining_apps


admin_site = GuessDleAdminSite(name="admin")
