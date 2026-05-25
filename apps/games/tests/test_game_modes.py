from django.contrib.auth.models import User
from django.db.models import Sum
from django.test import TestCase

from apps.accounts.models import GameElo
from apps.accounts.services.player_stats_service import PlayerStatsService
from apps.games.models import Game, GameItem, GameMode
from apps.games.services.generation_utils import generation_from_national_id, enrich_item_data
from apps.games.services.item_pool_service import ItemPoolService


class GameModeTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(name="Pokemon", slug="pokemon-test")
        self.normal = GameMode.objects.create(
            game=self.game,
            slug="normal",
            label="Normal",
            item_filter={"generacion__lte": 3},
        )
        self.radical = GameMode.objects.create(
            game=self.game,
            slug="radical",
            label="Radical",
            item_filter={},
        )
        for national_id, name in ((1, "bulbasaur"), (150, "mewtwo"), (400, "luxray"), (900, "sprigatito")):
            GameItem.objects.create(
                game=self.game,
                name=name,
                data=enrich_item_data({"id": national_id, "nombre": name}),
            )

    def test_generation_mapping(self):
        self.assertEqual(generation_from_national_id(1), 1)
        self.assertEqual(generation_from_national_id(386), 3)
        self.assertEqual(generation_from_national_id(649), 5)

    def test_pool_filters_by_generation(self):
        normal_count = ItemPoolService(self.game, self.normal).get_queryset().count()
        radical_count = ItemPoolService(self.game, self.radical).get_queryset().count()
        self.assertEqual(normal_count, 2)
        self.assertTrue(ItemPoolService(self.game, self.normal).contains_name("mewtwo"))
        self.assertEqual(radical_count, 4)

    def test_pool_description(self):
        self.assertEqual(
            self.normal.pool_description(),
            "Este modo incluye las 3 primeras generaciones.",
        )
        self.assertEqual(
            self.radical.pool_description(),
            "Este modo incluye todas las generaciones.",
        )

    def test_elo_per_mode(self):
        user = User.objects.create_user(username="player", password="x")
        GameElo.objects.create(user=user, game=self.game, mode=self.normal, elo=100)
        GameElo.objects.create(user=user, game=self.game, mode=self.radical, elo=200)
        self.assertEqual(PlayerStatsService.get_global_elo(user), 300)
        self.assertEqual(
            PlayerStatsService.get_game_stats(user, self.game, mode=self.normal)["points"],
            100,
        )
