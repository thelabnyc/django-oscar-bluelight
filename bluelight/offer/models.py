from django.db import models
from django.utils.translation import ugettext_lazy as _
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

        field_dict = dict(self.__dict__)
        for field in list(field_dict.keys()):
            if field.startswith('_'):
                del field_dict[field]

        # Custom proxy class
        if self.proxy_class:
            klass = utils.load_proxy(self.proxy_class)
            # Short-circuit again.
            if self.__class__ == klass:
                return self
            return klass(**field_dict)

        if self.type not in klassmap:
            raise RuntimeError("Unrecognised condition type (%s)" % self.type)

        # Check if we're using multi-table inheritance
        model_name = klassmap[self.type]._meta.model_name
        if hasattr(self, model_name):
            return getattr(self, model_name)

        # Must just be a standard proxy-model
        return klassmap[self.type](**field_dict)

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



from oscar.apps.offer.benefits import *
from .conditions import *

from oscar.apps.offer.benefits import __all__ as benefit_classes
from .conditions import __all__ as condition_classes
__all__.extend(benefit_classes)
__all__.extend(condition_classes)
