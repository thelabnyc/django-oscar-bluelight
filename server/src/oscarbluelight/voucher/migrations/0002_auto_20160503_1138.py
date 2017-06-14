# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
        ('voucher', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='voucher',
            name='groups',
            field=models.ManyToManyField(verbose_name='User Groups', to='auth.Group'),
        ),
        migrations.AddField(
            model_name='voucher',
            name='limit_usage_by_group',
            field=models.BooleanField(default=False, verbose_name='Limit usage to selected user groups'),
        ),
    ]
