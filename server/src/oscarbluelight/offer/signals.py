import django.dispatch


"""
Signal dispatched before offers are applied to a basket.
"""
pre_offers_apply = django.dispatch.Signal()


"""
Signal dispatched after offers are applied to a basket.
"""
post_offers_apply = django.dispatch.Signal()


"""
Signal dispatched before beginning to apply an offer group to a basket.
"""
pre_offer_group_apply = django.dispatch.Signal()


"""
Signal dispatched after applying an offer group to a basket.
"""
post_offer_group_apply = django.dispatch.Signal()

"""
Signal dispatched after the RangeProductSet materialized view has been refreshed.
"""
range_product_set_view_updated = django.dispatch.Signal()
