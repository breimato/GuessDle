from django.test import SimpleTestCase

from apps.games.services.catalog.one_piece_arc_order import (
    dedupe_arc_records,
    normalize_arc_slug,
    sort_arc_records,
)


class OnePieceArcOrderTests(SimpleTestCase):
    def test_sort_arc_records_follows_series_order(self):
        records = [
            {"slug": "marineford", "label": "Marineford"},
            {"slug": "romance_dawn", "label": "Romance Dawn"},
            {"slug": "wano", "label": "Wano"},
        ]
        ordered = sort_arc_records(records)
        self.assertEqual(
            [row["slug"] for row in ordered],
            ["romance_dawn", "marineford", "wano"],
        )

    def test_unknown_arcs_sort_after_canonical(self):
        records = [
            {"slug": "zzz_extra", "label": "Extra"},
            {"slug": "romance_dawn", "label": "Romance Dawn"},
        ]
        ordered = sort_arc_records(records)
        self.assertEqual([row["slug"] for row in ordered], ["romance_dawn", "zzz_extra"])

    def test_normalize_arc_slug_strips_accents(self):
        self.assertEqual(
            normalize_arc_slug("archipiélago_sabaody"),
            "archipielago_sabaody",
        )
        self.assertEqual(normalize_arc_slug("capítulo_0"), "capitulo_0")

    def test_dedupe_arc_records_merges_accented_slugs(self):
        records = [
            {"slug": "capítulo_0", "label": "Capítulo 0 A"},
            {"slug": "capitulo_0", "label": "Capítulo 0 B"},
        ]
        merged = dedupe_arc_records(records)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["slug"], "capitulo_0")

    def test_canonical_saga_order_from_wiki(self):
        slugs = [
            "enies_lobby",
            "water_7",
            "reverie",
            "wano",
            "whole_cake_island",
            "skypiea",
            "jaya",
            "archipiélago_sabaody",
            "zou",
            "dressrosa",
        ]
        records = [{"slug": slug, "label": slug} for slug in slugs]
        ordered = [row["slug"] for row in sort_arc_records(records)]
        self.assertEqual(
            ordered,
            [
                "jaya",
                "skypiea",
                "water_7",
                "enies_lobby",
                "archipielago_sabaody",
                "dressrosa",
                "zou",
                "whole_cake_island",
                "reverie",
                "wano",
            ],
        )
