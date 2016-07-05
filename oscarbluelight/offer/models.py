from oscar.apps.offer.abstract_models import (
    AbstractBenefit,
    AbstractCondition,
    AbstractConditionalOffer,
    AbstractRange,
    AbstractRangeProduct,
    AbstractRangeProductFileUpload
)
from oscar.apps.offer.results import (
    SHIPPING_DISCOUNT,
    ZERO_DISCOUNT,
    BasketDiscount,
    PostOrderAction,
    ShippingDiscount
)
import copy


__all__ = [
    'BasketDiscount', 'ShippingDiscount', 'PostOrderAction',
    'SHIPPING_DISCOUNT', 'ZERO_DISCOUNT'
]


class ConditionalOffer(AbstractConditionalOffer):
    pass
__all__.append('ConditionalOffer')



class Benefit(AbstractBenefit):
    pass
__all__.append('Benefit')



class Condition(AbstractCondition):
    COMPOUND = "Compound"

    def proxy(self):
        from . import conditions
        klassmap = {
            self.COUNT: conditions.CountCondition,
            self.VALUE: conditions.ValueCondition,
            self.COVERAGE: conditions.CoverageCondition,
            self.COMPOUND: conditions.CompoundCondition,
        }

        # Short-circuit logic if current class is already a proxy class.
        if self.__class__ in klassmap.values():
            return self

        # Custom proxy class
        if self.proxy_class:
            Klass = utils.load_proxy(self.proxy_class)
            return self._init_proxy(Klass)

        # Check if we're using multi-table inheritance
        model_name = klassmap[self.type]._meta.model_name
        if hasattr(self, model_name):
            return getattr(self, model_name)

        # Must just be a standard proxy-model
        if self.type not in klassmap:
            raise RuntimeError("Unrecognized condition type (%s)" % self.type)
        Klass = klassmap[self.type]
        return self._init_proxy(Klass)

    def _init_proxy(self, Klass):
        if self.__class__ == Klass:
            return self
        proxy = copy.deepcopy(self)
        proxy.__class__ = Klass
        return proxy


__all__.append('Condition')



class Range(AbstractRange):
    pass
__all__.append('Range')



class RangeProduct(AbstractRangeProduct):
    pass
__all__.append('RangeProduct')



class RangeProductFileUpload(AbstractRangeProductFileUpload):
    pass
__all__.append('RangeProductFileUpload')



from oscar.apps.offer.benefits import *  # NOQA
from .conditions import *  # NOQA

from oscar.apps.offer.benefits import __all__ as benefit_classes  # NOQA
from .conditions import __all__ as condition_classes  # NOQA

__all__.extend(benefit_classes)
__all__.extend(condition_classes)
