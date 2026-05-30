from django import template

from apps.games.services.extra.payout import format_extra_bet_goal

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')


@register.filter
def extra_bet_goal(value):
    return format_extra_bet_goal(value) or ""
