from django.test import TestCase

from apps.games.constants import (
    DAILY_WORDLE_MODE_LABEL,
    default_wordle_mode_label,
)


class ModeLabelTests(TestCase):
    def test_pokemon_keeps_normal_difficulty_label(self):
        self.assertEqual(default_wordle_mode_label("pokemon"), "Normal")
        self.assertEqual(default_wordle_mode_label("pokemon", "dificil"), "Difícil")

    def test_league_and_one_piece_use_diario(self):
        self.assertEqual(default_wordle_mode_label("league-of-legends"), DAILY_WORDLE_MODE_LABEL)
        self.assertEqual(default_wordle_mode_label("lol"), DAILY_WORDLE_MODE_LABEL)
        self.assertEqual(default_wordle_mode_label("one-piece"), DAILY_WORDLE_MODE_LABEL)
