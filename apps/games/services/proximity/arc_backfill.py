from apps.games.models import ArcCatalog, Game, GameItem
from apps.games.services.catalog.one_piece_arc_order import arc_sort_index, normalize_arc_slug
from apps.games.services.proximity.filter_service import slugify_arc_label
from apps.games.services.proximity.pool_service import ProximityPoolService


def backfill_arc_catalog(game: Game) -> tuple[int, int]:
    labels: dict[str, str] = {}
    updated_items = 0

    for item in GameItem.objects.filter(game=game, deleted=False):
        data = dict(item.data or {})
        slug = ProximityPoolService.arc_slug_from_item_data(data)
        label = data.get("arco de primera aparición") or data.get("arco")
        if not slug and label:
            slug = slugify_arc_label(str(label))
        slug = normalize_arc_slug(slug) if slug else ""
        if not slug:
            continue
        labels[slug] = str(label or slug.replace("_", " ").title())
        if data.get("arco_slug") != slug:
            data["arco_slug"] = slug
            item.data = data
            item.save(update_fields=["data"])
            updated_items += 1

    catalog_count = 0
    ordered_slugs = sorted(
        labels.keys(),
        key=lambda slug: (arc_sort_index(slug), labels[slug].lower()),
    )
    for sort_order, slug in enumerate(ordered_slugs):
        label = labels[slug]
        ArcCatalog.objects.update_or_create(
            game=game,
            slug=slug,
            defaults={"label": label, "sort_order": sort_order, "active": True},
        )
        catalog_count += 1

    ArcCatalog.objects.filter(game=game).exclude(slug__in=labels.keys()).update(active=False)
    return catalog_count, updated_items
