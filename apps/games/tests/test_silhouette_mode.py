from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import GameElo
from apps.games.models import (
    Game,
    GameItem,
    GameMode,
    GameModePlayType,
    SilhouetteDailyAssignment,
)
from apps.games.services.proximity.filter_service import ProximityFilterService
from apps.games.services.silhouette.anchor_service import SILHOUETTE_ANCHORS, resolve_anchor
from apps.games.services.silhouette.guess_processor import SilhouetteGuessProcessor
from apps.games.services.silhouette.pool_service import SilhouettePoolService
from apps.games.services.silhouette.target_service import SilhouetteTargetService


def _mock_image_url(_self):
    return "/media/game_item_images/pokemon/25.png"


class SilhouetteFilterTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(
            name="Pokemon Silueta",
            slug="pokemon-silueta-filters",
            data_source_url="https://example.com",
            attributes=["id", "generacion"],
        )

    def test_filters_use_proximity_defaults_gen_1_to_3(self):
        defaults = ProximityFilterService(self.game).defaults()
        self.assertEqual(defaults["generations"], [1, 2, 3])


class SilhouettePoolTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(
            name="Pokemon Silueta Pool",
            slug="pokemon-silueta-pool",
            data_source_url="https://example.com",
            attributes=["id", "generacion"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="silueta",
            play_type=GameModePlayType.SILHOUETTE,
        )
        self.with_image = GameItem.objects.create(
            game=self.game,
            name="Pikachu",
            data={"id": 25, "generacion": 1},
        )
        self.without_image = GameItem.objects.create(
            game=self.game,
            name="SinImagen",
            data={"id": 26, "generacion": 1},
        )

    @patch.object(GameItem, "get_image_url", _mock_image_url)
    def test_pool_excludes_items_without_image(self):
        def selective_image(self):
            if self.name == "Pikachu":
                return "/media/game_item_images/pokemon/25.png"
            return None

        with patch.object(GameItem, "get_image_url", selective_image):
            pool = SilhouettePoolService(
                self.game,
                self.mode,
                {"generations": [1]},
            )
            names = list(pool.item_queryset().values_list("name", flat=True))
            self.assertEqual(names, ["Pikachu"])


class SilhouetteAnchorTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(
            name="Pokemon Silueta Anchor",
            slug="pokemon-silueta-anchor",
            data_source_url="https://example.com",
            attributes=["id"],
        )
        self.item = GameItem.objects.create(
            game=self.game,
            name="Pikachu",
            data={"id": 25, "generacion": 1},
        )
        self.user = User.objects.create_user(username="anchor_user", password="pass")

    def test_assignment_picks_anchor_corner(self):
        assignment_date = timezone.localdate()
        anchor = resolve_anchor(self.item, assignment_date, self.user.pk)
        self.assertIn(anchor, SILHOUETTE_ANCHORS)

        second = resolve_anchor(self.item, assignment_date, self.user.pk)
        self.assertEqual(anchor, second)


class SilhouetteGuessProcessorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="silhouette_player", password="pass")
        self.game = Game.objects.create(
            name="Pokemon Silueta Play",
            slug="pokemon-silueta-play",
            data_source_url="https://example.com",
            attributes=["id", "generacion"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="silueta",
            play_type=GameModePlayType.SILHOUETTE,
        )
        self.target = GameItem.objects.create(
            game=self.game,
            name="Pikachu",
            data={"id": 25, "generacion": 1},
        )
        self.other = GameItem.objects.create(
            game=self.game,
            name="Raichu",
            data={"id": 26, "generacion": 1},
        )
        self.assignment = SilhouetteDailyAssignment.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            date=timezone.localdate(),
            is_team=False,
            filter_config={"generations": [1]},
            target_item=self.target,
            anchor="tl",
        )
        GameElo.objects.create(user=self.user, game=self.game, mode=self.mode, elo=100)

    def _processor(self):
        return SilhouetteGuessProcessor(self.game, self.mode, self.user)

    def _post(self, name: str):
        class Request:
            POST = {"guess": name}

        return Request()

    @patch.object(GameItem, "get_image_url", _mock_image_url)
    def test_wrong_guess_increments_zoom_level(self):
        GameItem.objects.create(
            game=self.game,
            name="Bulbasaur",
            data={"id": 1, "generacion": 1},
        )
        processor = self._processor()
        _, first_state = processor.process(self._post("Raichu"), self.assignment)
        self.assertEqual(first_state["zoom_level"], 1)

        _, second_state = processor.process(self._post("Bulbasaur"), self.assignment)
        self.assertEqual(second_state["zoom_level"], 2)

    @patch.object(GameItem, "get_image_url", _mock_image_url)
    def test_unlimited_wrong_guesses_allowed(self):
        processor = self._processor()
        wrong_names = [
            "Raichu",
            "Bulbasaur",
            "Charmander",
            "Squirtle",
            "Caterpie",
            "Weedle",
            "Pidgey",
            "Rattata",
            "Spearow",
            "Ekans",
        ]
        for name in wrong_names:
            GameItem.objects.get_or_create(
                game=self.game,
                name=name,
                defaults={"data": {"id": 99, "generacion": 1}},
            )

        state = None
        for name in wrong_names:
            _, state = processor.process(self._post(name), self.assignment)

        self.assertTrue(state["can_play"])
        self.assertFalse(state["won"])

    @patch.object(GameItem, "get_image_url", _mock_image_url)
    def test_correct_guess_ends_game(self):
        processor = self._processor()
        _, state = processor.process(self._post("Pikachu"), self.assignment)
        self.assertTrue(state["won"])
        self.assertFalse(state["can_play"])

    @patch.object(GameItem, "get_image_url", _mock_image_url)
    def test_no_elo_on_completion(self):
        processor = self._processor()
        processor.process(self._post("Pikachu"), self.assignment)
        self.assertEqual(
            GameElo.objects.get(user=self.user, game=self.game, mode=self.mode).elo,
            100,
        )


class SilhouetteViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="silhouette_view", password="pass")
        self.client = Client()
        self.client.force_login(self.user)
        self.game = Game.objects.create(
            name="Pokemon Silueta View",
            slug="pokemon",
            data_source_url="https://example.com",
            attributes=["id", "generacion"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="silueta",
            play_type=GameModePlayType.SILHOUETTE,
        )
        self.target = GameItem.objects.create(
            game=self.game,
            name="Pikachu",
            data={"id": 25, "generacion": 1},
        )

    @patch.object(GameItem, "get_image_url", _mock_image_url)
    def test_play_page_renders_silhouette_viewport(self):
        SilhouetteDailyAssignment.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            date=timezone.localdate(),
            is_team=False,
            filter_config={"generations": [1, 2, 3]},
            target_item=self.target,
            anchor="tr",
        )
        url = reverse("play_mode", args=[self.game.slug, self.mode.slug])
        response = self.client.get(url)
        self.assertContains(response, "proximity-pokedex")
        self.assertContains(response, "proximity-pokedex__screen")
        self.assertContains(response, "silhouette-viewport")
        self.assertContains(response, "silhouette-sprite")
        self.assertContains(response, 'data-anchor="tr"')

    @patch.object(GameItem, "get_image_url", _mock_image_url)
    def test_filters_page_renders_proximity_template(self):
        url = reverse("silhouette_filters", args=[self.game.slug, self.mode.slug])
        response = self.client.get(url)
        self.assertContains(response, "¿Con qué generaciones quieres jugar?")
        self.assertTemplateUsed(response, "games/proximity_filters.html")

    @patch.object(GameItem, "get_image_url", _mock_image_url)
    def test_filters_locked_after_first_guess(self):
        assignment = SilhouetteTargetService(
            self.game, self.user, self.mode
        ).ensure_assignment({"generations": [1, 2, 3]})
        processor = SilhouetteGuessProcessor(self.game, self.mode, self.user)

        class Request:
            POST = {"guess": "MissingMon"}

        with patch.object(GameItem, "get_image_url", _mock_image_url):
            GameItem.objects.create(
                game=self.game,
                name="MissingMon",
                data={"id": 10, "generacion": 1},
            )
            processor.process(Request(), assignment)

        filters_url = reverse("silhouette_filters", args=[self.game.slug, self.mode.slug])
        response = self.client.post(
            filters_url,
            {"generations": ["1"]},
        )
        self.assertRedirects(
            response,
            reverse("play_mode", args=[self.game.slug, self.mode.slug]),
            fetch_redirect_response=False,
        )
