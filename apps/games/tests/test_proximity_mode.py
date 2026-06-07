import random
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import GameElo, UserProfile
from apps.games.models import (
    Game,
    GameItem,
    GameMode,
    GameModePlayType,
    PlaySession,
    PlaySessionType,
    ProximityDailyAssignment,
    ProximityPrompt,
)
from apps.games.services.proximity.filter_service import ProximityFilterService
from apps.games.services.proximity.game_config import (
    TEAM_TIMER_SECONDS,
    proximity_info_text,
)
from apps.games.services.proximity.guess_processor import ProximityGuessProcessor
from apps.games.services.proximity.pool_service import ProximityPoolService
from apps.games.services.proximity.score_service import ProximityScoreService
from apps.games.services.proximity.session_service import ProximitySessionService
from apps.games.services.proximity.target_service import ProximityTargetService
from apps.games.services.proximity.timeout_service import ProximityTimeoutService
from apps.games.services.proximity.weighted_picker import pick_weighted_item


class ProximityDistanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="prox_user", password="pass")
        self.game = Game.objects.create(
            name="LoL Prox",
            slug="lol-prox",
            data_source_url="https://example.com",
            attributes=["releaseDate"],
            numeric_fields=["releaseDate"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="proximidad",
            label="Proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        self.item = GameItem.objects.create(
            game=self.game,
            name="Ahri",
            data={"releaseDate": 2011, "id": 2},
        )
        self.assignment = ProximityDailyAssignment.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            date=timezone.localdate(),
            is_team=False,
            filter_config={"years": list(range(2009, 2027))},
            target_item=self.item,
            answer_value=2011,
        )

    def test_single_guess_completes_and_reveals_answer(self):
        client = Client()
        client.force_login(self.user)
        url = reverse("proximity_guess", args=[self.game.slug, self.mode.slug])
        response = client.post(url, {"guess": "2020"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["won"])
        self.assertFalse(payload["can_play"])
        self.assertEqual(payload["score_locked"], 9)
        self.assertEqual(payload["answer_value"], 2011)

    def test_second_guess_is_rejected(self):
        processor = ProximityGuessProcessor(self.game, self.mode, self.user)

        class FakeRequest:
            POST = {"guess": "2020"}

        processor.process(FakeRequest(), self.assignment)
        ok, payload = processor.process(FakeRequest(), self.assignment)
        self.assertFalse(ok)
        self.assertIn("partida", payload["error"].lower())

    def test_guess_outside_bounds_is_rejected(self):
        processor = ProximityGuessProcessor(self.game, self.mode, self.user)

        class FakeRequest:
            POST = {"guess": "1999"}

        ok, payload = processor.process(FakeRequest(), self.assignment)
        self.assertFalse(ok)
        self.assertIn("entre", payload["error"].lower())

    def test_filters_locked_after_guess(self):
        client = Client()
        client.force_login(self.user)
        client.post(
            reverse("proximity_guess", args=[self.game.slug, self.mode.slug]),
            {"guess": "2020"},
        )
        filters_url = reverse("proximity_filters", args=[self.game.slug, self.mode.slug])
        response = client.get(filters_url)
        self.assertRedirects(
            response,
            reverse("play_mode", args=[self.game.slug, self.mode.slug]),
        )
        play_response = client.get(
            reverse("play_mode", args=[self.game.slug, self.mode.slug])
        )
        self.assertNotContains(play_response, "play-nav__filters")

    def test_symmetric_distance_same_score(self):
        sym_item = GameItem.objects.create(
            game=self.game,
            name="Sym Champ",
            data={"releaseDate": 2015, "id": 3},
        )
        assignment = ProximityDailyAssignment.objects.create(
            user=User.objects.create_user(username="sym", password="pass"),
            game=self.game,
            mode=self.mode,
            date=timezone.localdate(),
            is_team=False,
            filter_config={"years": list(range(2009, 2027))},
            target_item=sym_item,
            answer_value=2015,
        )
        processor = ProximityGuessProcessor(self.game, self.mode, assignment.user)

        class FakeRequest:
            POST = {"guess": "2020"}

        _, high = processor.process(FakeRequest(), assignment)
        self.assertEqual(high["score_locked"], 5)


class ProximityTeamTimerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="team_user", password="pass")
        self.user.profile.is_team_account = True
        self.user.profile.save(update_fields=["is_team_account"])
        self.game = Game.objects.create(
            name="Team Prox",
            slug="team-prox",
            data_source_url="https://example.com",
            attributes=["releaseDate"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        self.item = GameItem.objects.create(
            game=self.game, name="X", data={"releaseDate": 2010, "id": 1}
        )
        self.assignment = ProximityDailyAssignment.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            date=timezone.localdate(),
            is_team=True,
            filter_config={"years": list(range(2009, 2027))},
            target_item=self.item,
            answer_value=2010,
        )

    def test_timeout_without_guess_has_no_score_penalty(self):
        session = ProximitySessionService.get_or_create(
            self.user, self.game, self.mode, self.assignment
        )
        session.proximity_started_at = timezone.now() - timedelta(seconds=TEAM_TIMER_SECONDS + 5)
        session.save(update_fields=["proximity_started_at"])

        ProximityTimeoutService(self.game, self.mode, self.user).fail_timed_out(session)
        session.refresh_from_db()

        self.assertTrue(session.proximity_timed_out)
        self.assertIsNone(session.proximity_score_locked)
        self.assertIsNone(session.proximity_first_distance)
        self.assertTrue(session.proximity_completed)

    def test_guess_after_deadline_is_rejected(self):
        session = ProximitySessionService.get_or_create(
            self.user, self.game, self.mode, self.assignment
        )
        session.proximity_started_at = timezone.now() - timedelta(seconds=TEAM_TIMER_SECONDS + 1)
        session.save(update_fields=["proximity_started_at"])

        processor = ProximityGuessProcessor(self.game, self.mode, self.user)

        class FakeRequest:
            POST = {"guess": "2015"}

        ok, payload = processor.process(FakeRequest(), self.assignment)
        self.assertFalse(ok)
        self.assertIn("tiempo", payload["error"].lower())

    def test_guess_within_deadline_works(self):
        session = ProximitySessionService.get_or_create(
            self.user, self.game, self.mode, self.assignment
        )
        ProximitySessionService.ensure_started(session, is_team=True)

        processor = ProximityGuessProcessor(self.game, self.mode, self.user)

        class FakeRequest:
            POST = {"guess": "2020"}

        ok, payload = processor.process(FakeRequest(), self.assignment)
        self.assertTrue(ok)
        self.assertEqual(payload["score_locked"], 10)

    def _past_deadline_processor(self):
        session = ProximitySessionService.get_or_create(
            self.user, self.game, self.mode, self.assignment
        )
        session.proximity_started_at = timezone.now() - timedelta(
            seconds=TEAM_TIMER_SECONDS + 1
        )
        session.save(update_fields=["proximity_started_at"])
        return ProximityGuessProcessor(self.game, self.mode, self.user)

    def test_timeout_with_pending_guess_records_distance(self):
        processor = self._past_deadline_processor()

        class FakeRequest:
            POST = {"guess": "2020"}

        ok, payload = processor.process_timeout(FakeRequest(), self.assignment)
        self.assertTrue(ok)
        self.assertFalse(payload["timed_out"])
        self.assertEqual(payload["score_locked"], 10)
        self.assertEqual(payload["first_guess_value"], 2020)

    def test_timeout_with_invalid_guess_treated_as_no_answer(self):
        processor = self._past_deadline_processor()

        class FakeRequest:
            POST = {"guess": "1999"}

        ok, payload = processor.process_timeout(FakeRequest(), self.assignment)
        self.assertTrue(ok)
        self.assertTrue(payload["timed_out"])
        self.assertIsNone(payload["score_locked"])
        self.assertIsNone(payload["first_guess_value"])


class ProximityFilterTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(
            name="Pokemon Prox",
            slug="pokemon-prox",
            data_source_url="https://example.com",
            attributes=["id", "generacion"],
            numeric_fields=["id"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        GameItem.objects.create(game=self.game, name="Bulbasaur", data={"id": 1, "generacion": 1})
        GameItem.objects.create(game=self.game, name="Chikorita", data={"id": 152, "generacion": 2})

    def test_generations_filter_reduces_pool(self):
        pool_all = ProximityPoolService(
            self.game, self.mode, {"generations": [1, 2]}
        ).item_queryset()
        self.assertEqual(pool_all.count(), 2)


class ProximityLolPoolTests(TestCase):
    def test_lol_pool_uses_ano_field(self):
        game = Game.objects.create(
            name="LoL Real",
            slug="lol-real-prox",
            data_source_url="https://example.com",
            attributes=["Año"],
            numeric_fields=["Año"],
        )
        mode = GameMode.objects.create(
            game=game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        GameItem.objects.create(
            game=game,
            name="Ahri",
            data={"Año": 2011, "id": 1},
        )
        GameItem.objects.create(
            game=game,
            name="Old",
            data={"Año": 2008, "id": 2},
        )
        pool = ProximityPoolService(
            game, mode, {"years": [2011]}
        ).item_queryset()
        self.assertEqual(pool.count(), 1)
        self.assertEqual(pool.first().name, "Ahri")

    def test_lol_filter_normalizes_legacy_year_range_to_years(self):
        game = Game.objects.create(
            name="LoL Legacy",
            slug="lol-legacy-prox",
            data_source_url="https://example.com",
            attributes=["releaseDate"],
        )
        GameItem.objects.create(game=game, name="A", data={"releaseDate": 2010})
        GameItem.objects.create(game=game, name="B", data={"releaseDate": 2011})
        GameItem.objects.create(game=game, name="C", data={"releaseDate": 2012})
        service = ProximityFilterService(game)
        config = service.normalize({"year_min": 2011, "year_max": 2012})
        self.assertEqual(config, {"years": [2011, 2012]})


class ProximityTargetAssignmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="target_user", password="pass")
        self.game = Game.objects.create(
            name="LoL Target",
            slug="lol-target-prox",
            data_source_url="https://example.com",
            attributes=["releaseDate"],
            numeric_fields=["releaseDate"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="proximidad",
            label="Proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        self.filter_config = {"years": [2010, 2011, 2012]}
        for index, year in enumerate([2010, 2011, 2012], start=1):
            GameItem.objects.create(
                game=self.game,
                name=f"Champ{index}",
                data={"releaseDate": year, "id": index},
            )

    def test_ensure_assignment_when_called_twice_same_day_then_returns_cached_target(self):
        service = ProximityTargetService(self.game, self.user, self.mode)
        first = service.ensure_assignment(self.filter_config)
        second = service.ensure_assignment(self.filter_config)

        self.assertIsNotNone(first)
        self.assertEqual(second.pk, first.pk)
        self.assertEqual(second.target_item_id, first.target_item_id)

    def test_ensure_assignment_when_recreated_same_filters_then_can_pick_different_target(self):
        service = ProximityTargetService(self.game, self.user, self.mode)
        outcomes: set[int] = set()

        for _ in range(20):
            ProximityDailyAssignment.objects.filter(
                user=self.user,
                game=self.game,
                mode=self.mode,
                date=timezone.localdate(),
            ).delete()
            assignment = service.ensure_assignment(self.filter_config)
            self.assertIsNotNone(assignment)
            outcomes.add(assignment.target_item_id)

        self.assertGreater(len(outcomes), 1)


class ProximityEloTests(TestCase):
    def test_score_is_literal_distance(self):
        self.assertEqual(ProximityScoreService.points_for_distance(25), 25)
        self.assertEqual(ProximityScoreService.points_for_distance(0), 0)

    def test_single_guess_adds_distance_to_elo(self):
        user = User.objects.create_user(username="elo_user", password="pass")
        game = Game.objects.create(
            name="Elo Prox",
            slug="elo-prox",
            data_source_url="https://example.com",
            attributes=["releaseDate"],
        )
        mode = GameMode.objects.create(
            game=game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        item = GameItem.objects.create(game=game, name="X", data={"releaseDate": 2010, "id": 1})
        assignment = ProximityDailyAssignment.objects.create(
            user=user,
            game=game,
            mode=mode,
            date=timezone.localdate(),
            is_team=False,
            filter_config={"years": list(range(2009, 2027))},
            target_item=item,
            answer_value=2010,
        )
        processor = ProximityGuessProcessor(game, mode, user)

        class FakeRequest:
            POST = {"guess": "2020"}

        processor.process(FakeRequest(), assignment)
        elo = GameElo.objects.get(user=user, game=game, mode=mode)
        self.assertEqual(elo.elo, 10)


class ProximityEventPromptTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="op_user", password="pass")
        self.game = Game.objects.create(
            name="One Piece",
            slug="one-piece-test",
            data_source_url="https://example.com",
            attributes=["capitulo"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        self.prompt = ProximityPrompt.objects.create(
            game=self.game,
            prompt_text="Ace muere en Marineford",
            answer_value=574,
            arcs=["marineford"],
        )
        self.assignment = ProximityDailyAssignment.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            date=timezone.localdate(),
            is_team=False,
            filter_config={"arcs": ["marineford"], "media": "manga"},
            proximity_prompt=self.prompt,
            answer_value=574,
        )

    def test_event_prompt_text_in_play_page(self):
        client = Client()
        client.force_login(self.user)
        url = reverse("play_mode", args=[self.game.slug, self.mode.slug])
        response = client.get(url)
        self.assertContains(response, "Ace muere en Marineford")


class ProximityInfoTextTests(TestCase):
    def test_pokemon_info_text(self):
        game = Game.objects.create(name="Pokemon", slug="pokemon", attributes=["id"])
        text = proximity_info_text(game)
        self.assertIn("Pokédex", text)
        self.assertIn("un solo intento", text)
        self.assertIn("1 minuto", text)

    def test_lol_info_text(self):
        game = Game.objects.create(name="LoL", slug="league-of-legends", attributes=["Año"])
        text = proximity_info_text(game)
        self.assertIn("año de lanzamiento", text)
        self.assertIn("campeón", text)
        self.assertIn("1 minuto", text)

    def test_one_piece_info_text(self):
        game = Game.objects.create(name="One Piece", slug="one-piece", attributes=["capitulo"])
        text = proximity_info_text(game)
        self.assertIn("primera aparición", text)
        self.assertIn("evento", text)
        self.assertIn("manga", text)
        self.assertIn("episodio", text)
        self.assertIn("1 minuto", text)

    def test_mode_pool_description_uses_game_specific_proximity_text(self):
        game = Game.objects.create(name="Pokemon", slug="pokemon-test-info", attributes=["id"])
        mode = GameMode.objects.create(
            game=game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        self.assertEqual(mode.pool_description(), proximity_info_text(game))


class ProximityPromptImportTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(
            name="One Piece",
            slug="one-piece-import",
            attributes=["capitulo"],
        )

    def test_import_stores_answer_episode(self):
        from apps.games.services.proximity.prompt_importer import import_proximity_prompts

        payload = [
            {
                "prompt": "Ace muere en Marineford",
                "answer_chapter": 574,
                "answer_episode": 483,
                "arcs": ["marineford"],
                "kind": "event",
            }
        ]
        count = import_proximity_prompts(self.game, payload)
        self.assertEqual(count, 1)
        prompt = self.game.proximity_prompts.get()
        self.assertEqual(prompt.answer_value, 574)
        self.assertEqual(prompt.answer_episode, 483)


class ProximityAnimeModeTests(TestCase):
    def test_prompt_resolver_uses_episode_in_anime_mode(self):
        from apps.games.models import ProximityPrompt
        from apps.games.services.proximity.answer_resolver import ProximityAnswerResolver

        game = Game.objects.create(name="OP", slug="one-piece-anime", attributes=["capitulo"])
        prompt = ProximityPrompt.objects.create(
            game=game,
            prompt_text="Test",
            answer_value=574,
            answer_episode=483,
        )
        resolver = ProximityAnswerResolver(game, media="anime")
        self.assertEqual(resolver.resolve_prompt(prompt), 483)

    def test_guess_processor_value_unit_for_anime(self):
        from apps.games.models import ProximityPrompt
        from apps.games.services.proximity.guess_processor import ProximityGuessProcessor

        user = User.objects.create_user(username="anime_user", password="pass")
        game = Game.objects.create(name="OP", slug="one-piece-anime-guess", attributes=["capitulo"])
        mode = GameMode.objects.create(
            game=game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        prompt = ProximityPrompt.objects.create(
            game=game,
            prompt_text="Ace muere",
            answer_value=574,
            answer_episode=483,
        )
        assignment = ProximityDailyAssignment.objects.create(
            user=user,
            game=game,
            mode=mode,
            date=timezone.localdate(),
            is_team=False,
            filter_config={"arcs": ["marineford"], "media": "anime"},
            proximity_prompt=prompt,
            answer_value=483,
        )
        session = ProximitySessionService.get_or_create(user, game, mode, assignment)
        state = ProximityGuessProcessor(game, mode, user).build_state(session, assignment)
        self.assertEqual(state["value_unit"], "episodio")

    def test_character_anime_resolves_episode_not_stored_chapter(self):
        user = User.objects.create_user(username="anime_char", password="pass")
        game = Game.objects.create(
            name="OP",
            slug="one-piece-anime-char",
            attributes=["capitulo"],
        )
        mode = GameMode.objects.create(
            game=game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        item = GameItem.objects.create(
            game=game,
            name="Chopper",
            data={"capítulo": 134, "episodio": 81, "arco_slug": "drum"},
        )
        assignment = ProximityDailyAssignment.objects.create(
            user=user,
            game=game,
            mode=mode,
            date=timezone.localdate(),
            is_team=False,
            filter_config={"arcs": ["drum"], "media": "anime"},
            target_item=item,
            answer_value=134,
        )
        processor = ProximityGuessProcessor(game, mode, user)

        class FakeRequest:
            POST = {"guess": "81"}

        ok, payload = processor.process(FakeRequest(), assignment)
        self.assertTrue(ok)
        self.assertTrue(payload["won"])
        self.assertEqual(payload["answer_value"], 81)

    def test_roster_chapters_have_episode_in_map(self):
        from apps.games.services.proximity.chapter_episode_lookup import episode_for_chapter

        game = Game.objects.create(name="OP", slug="one-piece-map-roster", attributes=["capitulo"])
        chapters = [3, 114, 134, 574, 1130]
        for chapter in chapters:
            self.assertIsNotNone(
                episode_for_chapter(chapter),
                f"capítulo {chapter} sin episodio en el mapa",
            )
        self.assertEqual(episode_for_chapter(3), 2)
        self.assertEqual(episode_for_chapter(114), 67)
        self.assertEqual(episode_for_chapter(134), 81)
        self.assertEqual(episode_for_chapter(1130), 1160)

    def test_filter_defaults_keep_media_when_filling_arcs(self):
        from apps.games.models import ArcCatalog
        from apps.games.services.proximity.filter_service import ProximityFilterService

        game = Game.objects.create(name="OP", slug="one-piece-defaults", attributes=["capitulo"])
        ArcCatalog.objects.create(game=game, slug="romance_dawn", label="Romance Dawn", sort_order=1)
        defaults = ProximityFilterService(game).defaults()
        self.assertEqual(defaults["media"], "manga")
        self.assertIn("romance_dawn", defaults["arcs"])


class OnePiecePickerCatalogTests(TestCase):
    def test_catalog_groups_follow_arc_choices_order_not_alphabetical(self):
        from apps.games.models import ArcCatalog
        from apps.games.services.proximity.picker_catalog_service import (
            ProximityPickerCatalogService,
        )

        game = Game.objects.create(name="OP", slug="one-piece", attributes=["capitulo"])
        mode = GameMode.objects.create(
            game=game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        ArcCatalog.objects.create(
            game=game, slug="marineford", label="Marineford", sort_order=2, active=True
        )
        ArcCatalog.objects.create(
            game=game, slug="romance_dawn", label="Romance Dawn", sort_order=1, active=True
        )
        GameItem.objects.create(
            game=game,
            name="Luffy",
            data={"capítulo": 1, "arco_slug": "romance_dawn"},
        )
        GameItem.objects.create(
            game=game,
            name="Ace",
            data={"capítulo": 574, "arco_slug": "marineford"},
        )

        filter_config = {"arcs": ["romance_dawn", "marineford"], "media": "manga"}
        catalog = ProximityPickerCatalogService(game, mode, filter_config).build()

        group_ids = [group["id"] for group in catalog["groups"]]
        self.assertEqual(group_ids, ["romance_dawn", "marineford"])

    def test_anime_catalog_includes_prompt_episodes_beyond_characters(self):
        from apps.games.models import ArcCatalog
        from apps.games.services.proximity.picker_catalog_service import (
            ProximityPickerCatalogService,
        )

        game = Game.objects.create(name="OP", slug="one-piece-anime-catalog", attributes=["capitulo"])
        mode = GameMode.objects.create(
            game=game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        ArcCatalog.objects.create(
            game=game, slug="thriller_bark", label="Thriller Bark", sort_order=1, active=True
        )
        GameItem.objects.create(
            game=game,
            name="Perona",
            data={"capítulo": 480, "episodio": 340, "arco_slug": "thriller_bark"},
        )
        ProximityPrompt.objects.create(
            game=game,
            prompt_text="Zoro toma el dolor de Luffy de Kuma en Thriller Bark",
            answer_value=485,
            answer_episode=377,
            arcs=["thriller_bark"],
        )

        filter_config = {"arcs": ["thriller_bark"], "media": "anime"}
        catalog = ProximityPickerCatalogService(game, mode, filter_config).build()

        thriller_group = next(group for group in catalog["groups"] if group["id"] == "thriller_bark")
        guess_values = [entry["guess_value"] for entry in thriller_group["entries"]]
        self.assertIn(340, guess_values)
        self.assertIn(377, guess_values)
        self.assertEqual(max(guess_values), 377)

        event_entry = next(entry for entry in thriller_group["entries"] if entry["guess_value"] == 377)
        self.assertEqual(event_entry["name"], "Episodio 377")
        self.assertNotIn("Zoro", event_entry["name"])

    def test_picker_catalog_entry_name_is_number_only(self):
        from apps.games.models import ArcCatalog
        from apps.games.services.proximity.picker_catalog_service import (
            ProximityPickerCatalogService,
        )

        game = Game.objects.create(name="OP", slug="one-piece-picker-name", attributes=["capitulo"])
        mode = GameMode.objects.create(
            game=game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        ArcCatalog.objects.create(
            game=game, slug="thriller_bark", label="Thriller Bark", sort_order=1, active=True
        )
        ProximityPrompt.objects.create(
            game=game,
            prompt_text="Zoro toma el dolor de Luffy de Kuma",
            answer_value=485,
            answer_episode=377,
            arcs=["thriller_bark"],
        )

        filter_config = {"arcs": ["thriller_bark"], "media": "manga"}
        catalog = ProximityPickerCatalogService(game, mode, filter_config).build()
        thriller_group = next(group for group in catalog["groups"] if group["id"] == "thriller_bark")
        event_entry = next(entry for entry in thriller_group["entries"] if entry["guess_value"] == 485)
        self.assertEqual(event_entry["name"], "Capítulo 485")
        self.assertNotIn("Zoro", event_entry["name"])

    def test_sanitize_proximity_prompt_text_strips_arc_reference(self):
        from apps.games.services.proximity.prompt_text_sanitizer import (
            sanitize_proximity_prompt_text,
        )

        self.assertEqual(
            sanitize_proximity_prompt_text(
                "Zoro toma el dolor de Luffy de Kuma en Thriller Bark"
            ),
            "Zoro toma el dolor de Luffy de Kuma",
        )
        self.assertEqual(
            sanitize_proximity_prompt_text("Ace muere protegiendo a Luffy en Marineford"),
            "Ace muere protegiendo a Luffy",
        )
        self.assertEqual(
            sanitize_proximity_prompt_text(
                "El timeskip: la tripulación se reúne en Sabaody dos años después"
            ),
            "El timeskip: la tripulación se reúne dos años después",
        )

    def test_import_proximity_prompts_applies_sanitizer(self):
        from apps.games.services.proximity.prompt_importer import import_proximity_prompts

        game = Game.objects.create(name="OP", slug="one-piece-import-sanitize", attributes=["capitulo"])
        payload = [
            {
                "prompt": "Brook se une a los Sombrero de Paja en Thriller Bark",
                "answer_chapter": 489,
                "answer_episode": 381,
                "arcs": ["thriller_bark"],
                "kind": "event",
            }
        ]
        import_proximity_prompts(game, payload)
        prompt = game.proximity_prompts.get()
        self.assertEqual(prompt.prompt_text, "Brook se une a los Sombrero de Paja")

    def test_whiskey_peak_prompt_is_specific_event(self):
        from apps.games.services.proximity.prompt_importer import import_proximity_prompts

        game = Game.objects.create(name="OP", slug="one-piece-whiskey-prompt", attributes=["capitulo"])
        payload = [
            {
                "prompt": (
                    "Zoro derrota solo a los agentes de Baroque Works "
                    "mientras la tripulación duerme"
                ),
                "answer_chapter": 115,
                "answer_episode": 70,
                "arcs": ["whiskey_peak"],
                "kind": "event",
            }
        ]
        import_proximity_prompts(game, payload)
        prompt = game.proximity_prompts.get()
        self.assertIn("Baroque Works", prompt.prompt_text)
        self.assertNotIn("entrena con los Sombrero", prompt.prompt_text)

    def test_arc_catalog_fills_continuous_range_between_pool_min_and_max(self):
        from apps.games.models import ArcCatalog
        from apps.games.services.proximity.picker_catalog_service import (
            ProximityPickerCatalogService,
        )

        game = Game.objects.create(name="OP", slug="one-piece-jaya-range", attributes=["capitulo"])
        mode = GameMode.objects.create(
            game=game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        ArcCatalog.objects.create(game=game, slug="jaya", label="Jaya", sort_order=1, active=True)
        GameItem.objects.create(
            game=game,
            name="Jesus Burgess",
            data={"capítulo": 222, "episodio": 146, "arco_slug": "jaya"},
        )
        GameItem.objects.create(
            game=game,
            name="Doc Q",
            data={"capítulo": 225, "episodio": 148, "arco_slug": "jaya"},
        )

        filter_config = {"arcs": ["jaya"], "media": "manga"}
        catalog = ProximityPickerCatalogService(game, mode, filter_config).build()

        jaya_group = next(group for group in catalog["groups"] if group["id"] == "jaya")
        guess_values = [entry["guess_value"] for entry in jaya_group["entries"]]
        self.assertEqual(guess_values, list(range(222, 226)))
        self.assertIn(224, guess_values)

    def test_wano_manga_catalog_includes_intermediate_chapter(self):
        from apps.games.models import ArcCatalog
        from apps.games.services.proximity.picker_catalog_service import (
            ProximityPickerCatalogService,
        )

        game = Game.objects.create(name="OP", slug="one-piece-wano-range", attributes=["capitulo"])
        mode = GameMode.objects.create(
            game=game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        ArcCatalog.objects.create(game=game, slug="wano", label="Wano", sort_order=1, active=True)
        GameItem.objects.create(
            game=game,
            name="Luffy",
            data={"capítulo": 913, "episodio": 898, "arco_slug": "wano"},
        )
        GameItem.objects.create(
            game=game,
            name="Kaido",
            data={"capítulo": 1050, "episodio": 1080, "arco_slug": "wano"},
        )

        filter_config = {"arcs": ["wano"], "media": "manga"}
        catalog = ProximityPickerCatalogService(game, mode, filter_config).build()

        wano_group = next(group for group in catalog["groups"] if group["id"] == "wano")
        guess_values = [entry["guess_value"] for entry in wano_group["entries"]]
        self.assertEqual(len(guess_values), 1050 - 913 + 1)
        self.assertIn(950, guess_values)
        self.assertEqual(guess_values[0], 913)
        self.assertEqual(guess_values[-1], 1050)

    def test_jaya_manga_catalog_min_is_222_without_teach_in_jaya(self):
        from apps.games.models import ArcCatalog
        from apps.games.services.proximity.picker_catalog_service import (
            ProximityPickerCatalogService,
        )

        game = Game.objects.create(name="OP", slug="one-piece-jaya-min", attributes=["capitulo"])
        mode = GameMode.objects.create(
            game=game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        ArcCatalog.objects.create(game=game, slug="jaya", label="Jaya", sort_order=1, active=True)
        ArcCatalog.objects.create(
            game=game, slug="isla_drum", label="Isla Drum", sort_order=2, active=True
        )
        GameItem.objects.create(
            game=game,
            name="Marshall D. Teach",
            data={"capítulo": 146, "episodio": 87, "arco_slug": "isla_drum"},
        )
        GameItem.objects.create(
            game=game,
            name="Jesus Burgess",
            data={"capítulo": 222, "episodio": 146, "arco_slug": "jaya"},
        )

        filter_config = {"arcs": ["jaya"], "media": "manga"}
        catalog = ProximityPickerCatalogService(game, mode, filter_config).build()

        jaya_group = next(group for group in catalog["groups"] if group["id"] == "jaya")
        guess_values = [entry["guess_value"] for entry in jaya_group["entries"]]
        self.assertEqual(min(guess_values), 222)
        self.assertNotIn(146, guess_values)

    def test_burgess_manga_guess_222_wins(self):
        user = User.objects.create_user(username="burgess_manga", password="pass")
        game = Game.objects.create(name="OP", slug="one-piece-burgess-manga", attributes=["capitulo"])
        mode = GameMode.objects.create(
            game=game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        item = GameItem.objects.create(
            game=game,
            name="Jesus Burgess",
            data={"capítulo": 222, "episodio": 146, "arco_slug": "jaya"},
        )
        assignment = ProximityDailyAssignment.objects.create(
            user=user,
            game=game,
            mode=mode,
            date=timezone.localdate(),
            is_team=False,
            filter_config={"arcs": ["jaya"], "media": "manga"},
            target_item=item,
            answer_value=222,
        )
        processor = ProximityGuessProcessor(game, mode, user)

        class FakeRequest:
            POST = {"guess": "222"}

        ok, payload = processor.process(FakeRequest(), assignment)
        self.assertTrue(ok)
        self.assertTrue(payload["won"])
        self.assertEqual(payload["answer_value"], 222)

    def test_burgess_anime_guess_146_wins(self):
        user = User.objects.create_user(username="burgess_anime", password="pass")
        game = Game.objects.create(name="OP", slug="one-piece-burgess-anime", attributes=["capitulo"])
        mode = GameMode.objects.create(
            game=game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        item = GameItem.objects.create(
            game=game,
            name="Jesus Burgess",
            data={"capítulo": 222, "episodio": 146, "arco_slug": "jaya"},
        )
        assignment = ProximityDailyAssignment.objects.create(
            user=user,
            game=game,
            mode=mode,
            date=timezone.localdate(),
            is_team=False,
            filter_config={"arcs": ["jaya"], "media": "anime"},
            target_item=item,
            answer_value=146,
        )
        processor = ProximityGuessProcessor(game, mode, user)

        class FakeRequest:
            POST = {"guess": "146"}

        ok, payload = processor.process(FakeRequest(), assignment)
        self.assertTrue(ok)
        self.assertTrue(payload["won"])
        self.assertEqual(payload["answer_value"], 146)


class LolPickerCatalogTests(TestCase):
    def test_lol_catalog_omits_champion_portraits_per_year(self):
        from apps.games.services.proximity.picker_catalog_service import (
            ProximityPickerCatalogService,
        )

        game = Game.objects.create(
            name="LoL",
            slug="league-of-legends",
            data_source_url="https://example.com",
            attributes=["releaseDate"],
            numeric_fields=["releaseDate"],
        )
        mode = GameMode.objects.create(
            game=game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        GameItem.objects.create(
            game=game,
            name="Ahri",
            data={"releaseDate": 2011, "id": 1},
        )

        filter_config = {"years": list(range(2009, 2027))}
        catalog = ProximityPickerCatalogService(game, mode, filter_config).build()

        year_entry = next(entry for entry in catalog["years"] if entry["year"] == 2011)
        self.assertEqual(year_entry, {"year": 2011})
        self.assertNotIn("image_url", year_entry)
