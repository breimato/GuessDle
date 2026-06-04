from django.test import TestCase

from apps.games.models import Game
from apps.games.services.catalog.generation_utils import enrich_item_data
from apps.games.services.catalog.one_piece_episode_utils import enrich_one_piece_episode


class OnePieceEpisodeUtilsTests(TestCase):
    def setUp(self):
        self.pokemon = Game.objects.create(name="Pokemon", slug="pokemon", attributes=["id"])
        self.one_piece = Game.objects.create(
            name="One Piece", slug="one-piece", attributes=["capitulo"]
        )
        self.lol = Game.objects.create(
            name="LoL", slug="league-of-legends", attributes=["Año"]
        )

    def test_enrich_adds_episodio_from_chapter(self):
        data = enrich_one_piece_episode({"capítulo": 134})
        self.assertEqual(data["episodio"], 81)

    def test_enrich_item_data_adds_episodio_for_one_piece(self):
        data = enrich_item_data({"capítulo": 3, "nombre": "Zoro"}, game=self.one_piece)
        self.assertEqual(data["episodio"], 2)

    def test_enrich_item_data_does_not_add_pokemon_generacion(self):
        data = enrich_item_data(
            {"capítulo": 3, "id": 152, "nombre": "Robin"}, game=self.one_piece
        )
        self.assertNotIn("generacion", data)
        self.assertEqual(data["episodio"], 2)

    def test_enrich_item_data_adds_generacion_only_for_pokemon(self):
        data = enrich_item_data({"id": 152, "nombre": "Chikorita"}, game=self.pokemon)
        self.assertEqual(data["generacion"], 2)

    def test_enrich_item_data_strips_generacion_from_lol(self):
        data = enrich_item_data(
            {"id": 152, "nombre": "Ahri", "generacion": 2, "Año": 2011}, game=self.lol
        )
        self.assertNotIn("generacion", data)
