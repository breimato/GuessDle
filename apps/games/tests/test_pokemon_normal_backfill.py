from django.contrib.auth.models import User
from django.test import TestCase

from apps.accounts.models import Challenge, GameElo
from apps.games.models import DailyTarget, ExtraDailyPlay, Game, GameItem, GameMode, PlaySession
from apps.games.services.pokemon_normal_backfill import backfill_pokemon_normal_mode


class PokemonNormalBackfillTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="ash", password="pass")
        self.game = Game.objects.create(name="Pokemon", slug="pokemon", active=True)
        self.normal_mode = GameMode.objects.create(
            game=self.game,
            slug="normal",
            label="Normal",
            sort_order=0,
        )
        GameMode.objects.create(
            game=self.game,
            slug="dificil",
            label="Dificil",
            sort_order=1,
        )
        self.target = GameItem.objects.create(game=self.game, name="Pikachu")

    def test_backfill_moves_legacy_stats_to_normal_mode(self):
        GameElo.objects.create(user=self.user, game=self.game, elo=120, partidas=4)
        PlaySession.objects.create(user=self.user, game=self.game, reference_id=1)
        DailyTarget.objects.create(
            game=self.game,
            target=self.target,
            date="2026-01-01",
            is_team=False,
        )
        ExtraDailyPlay.objects.create(
            user=self.user,
            game=self.game,
            target=self.target,
        )
        Challenge.objects.create(
            challenger=self.user,
            opponent=User.objects.create_user(username="misty", password="pass"),
            game=self.game,
            target=self.target,
        )

        summary = backfill_pokemon_normal_mode()

        self.assertTrue(summary["game_found"])
        self.assertEqual(summary["game_elo_updated"], 1)
        self.assertEqual(summary["play_sessions"], 1)
        self.assertEqual(summary["daily_targets_updated"], 1)
        self.assertEqual(summary["extra_daily_plays"], 1)
        self.assertEqual(summary["challenges"], 1)

        self.assertFalse(GameElo.objects.filter(game=self.game, mode__isnull=True).exists())
        self.assertEqual(
            GameElo.objects.get(user=self.user, game=self.game, mode=self.normal_mode).elo,
            120,
        )
        self.assertTrue(
            PlaySession.objects.filter(user=self.user, game=self.game, mode=self.normal_mode).exists()
        )

    def test_backfill_merges_duplicate_game_elo_rows(self):
        rival = User.objects.create_user(username="gary", password="pass")
        GameElo.objects.create(user=rival, game=self.game, elo=80, partidas=2)
        GameElo.objects.create(
            user=rival,
            game=self.game,
            mode=self.normal_mode,
            elo=20,
            partidas=1,
        )

        summary = backfill_pokemon_normal_mode()

        self.assertEqual(summary["game_elo_merged"], 1)
        merged_row = GameElo.objects.get(user=rival, game=self.game, mode=self.normal_mode)
        self.assertEqual(merged_row.elo, 100)
        self.assertEqual(merged_row.partidas, 3)
