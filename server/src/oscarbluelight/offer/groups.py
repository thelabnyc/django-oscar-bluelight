from django.db import transaction
from django.db.models import Max
from django.utils.functional import SimpleLazyObject
from .signals import pre_offer_group_apply, post_offer_group_apply
import logging
import collections

logger = logging.getLogger(__name__)
_system_group_registry = collections.deque()
_receivers = collections.deque()


@transaction.atomic
def insupd_system_offer_group(slug, default_name=None):
    """
    Get or create a system offer group with the given ``slug``. If creating, assign the name from ``default_name``.
    """
    from .models import OfferGroup
    max_priority = OfferGroup.objects.all().aggregate(Max('priority')).get('priority__max')
    max_priority = max_priority or 999
    default_priority = max_priority + 1
    defaults = {
        'name': default_name or slug,
        'priority': default_priority,
    }
    group, created = OfferGroup.objects.get_or_create(slug=slug, is_system_group=True, defaults=defaults)
    if created:
        logger.info('Create system offer group: {}, priority {}'.format(group.slug, group.priority))
    return group


def register_system_offer_group(slug, default_name=None):
    """
    Register a system offer group (an offer group that referenced by code). Returns the OfferGroup instance.

    To get / create a system offer group, call this function somewhere in your code base and assign the
    result to a constant. The return value is a lazy evaluated function which will, on-first-access, create the
    OfferGroup. On subsequent accesses, it will simply fetch the offer group and return it.
    """
    lazy_group = SimpleLazyObject(lambda: insupd_system_offer_group(slug, default_name))
    _system_group_registry.append(lazy_group)
    return lazy_group


def ensure_all_system_groups_exist():
    """
    Force evaluation of all the lazy objects created thus far by ``register_system_offer_group``.
    """
    while len(_system_group_registry) > 0:
        group = _system_group_registry.popleft()
        if hasattr(group, '_setup'):
            group._setup()


def pre_offer_group_apply_receiver(offer_group_slug, **decorator_kwargs):
    """
    Decorator used to connect a signal receive to the pre_offer_group_apply signal *for a specific system offer group.*
    Handler will only be called when ``pre_offer_group_apply`` is sent with an offer_group object matching the
    group provided as a parameter. You should only use signals with system offer groups.
    """
    return _offer_group_receiver(pre_offer_group_apply, offer_group_slug, **decorator_kwargs)


def post_offer_group_apply_receiver(offer_group_slug, **decorator_kwargs):
    """
    Decorator used to connect a signal receive to the post_offer_group_apply signal *for a specific system offer group.*
    Handler will only be called when ``post_offer_group_apply`` is sent with an offer_group object matching the
    group provided as a parameter. You should only use signals with system offer groups.
    """
    return _offer_group_receiver(post_offer_group_apply, offer_group_slug, **decorator_kwargs)


def _offer_group_receiver(signal, offer_group_slug, **decorator_kwargs):
    """
    Private function used to implement the pre_offer_group_apply_receiver and post_offer_group_apply_receiver decorators.
    """
    def _decorator(func):
        from .models import OfferGroup

        # Build an interim lambda function to filter signal events down to just the group instance we're looking for
        def _receiver(sender, **kwargs):
            ensure_all_system_groups_exist()
            offer_group = OfferGroup.objects.filter(slug=offer_group_slug).first()
            if not offer_group:
                logger.error('Listener is attached to offer group {}, but no such offer group exists!'.format(offer_group_slug))
                return
            if not offer_group.is_system_group:
                logger.warning('You should not attach listens to non-system offer group {}.'.format(offer_group_slug))
            if kwargs.get('group') and kwargs['group'].pk == offer_group.pk:
                return func(sender, **kwargs)
            return None

        # Store a reference to this function in the module scope so that it doesn't get immediately GC'd
        _receivers.append(_receiver)

        # Connect the given function to the signal by way of our receiver filter
        signal.connect(_receiver, **decorator_kwargs)

        return func

    return _decorator
