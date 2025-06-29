from django.utils.translation import gettext_lazy as _


class Conjunction:
    AND, OR = ("AND", "OR")
    TYPE_CHOICES = (
        (AND, _("Logical AND")),
        (OR, _("Logical OR")),
    )
