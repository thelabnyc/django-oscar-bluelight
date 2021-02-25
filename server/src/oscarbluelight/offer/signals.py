import django.dispatch


"""
Signal dispatched before offers are applied to a basket.
"""
pre_offers_apply = django.dispatch.Signal(providing_args=["basket", "offers"])


"""
Signal dispatched after offers are applied to a basket.
"""
post_offers_apply = django.dispatch.Signal(providing_args=["basket", "offers"])


"""
Signal dispatched before beginning to apply an offer group to a basket.
"""
pre_offer_group_apply = django.dispatch.Signal(
    providing_args=["basket", "group", "offers"]
)


"""
Signal dispatched after applying an offer group to a basket.
"""
post_offer_group_apply = django.dispatch.Signal(
    providing_args=["basket", "group", "offers"]
)
