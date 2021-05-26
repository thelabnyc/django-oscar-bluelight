import django.dispatch


"""
Signal dispatched before offers are applied to a basket.

providing_args=["basket", "offers"]
"""
pre_offers_apply = django.dispatch.Signal()


"""
Signal dispatched after offers are applied to a basket.

providing_args=["basket", "offers"]
"""
post_offers_apply = django.dispatch.Signal()


"""
Signal dispatched before beginning to apply an offer group to a basket.

providing_args=["basket", "group", "offers"]
"""
pre_offer_group_apply = django.dispatch.Signal()


"""
Signal dispatched after applying an offer group to a basket.

providing_args=["basket", "group", "offers"]
"""
post_offer_group_apply = django.dispatch.Signal()
