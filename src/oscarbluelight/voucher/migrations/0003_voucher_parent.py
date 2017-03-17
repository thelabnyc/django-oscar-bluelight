# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('voucher', '0002_auto_20160503_1138'),
    ]

    operations = [
        migrations.AddField(
            model_name='voucher',
            name='parent',
            field=models.ForeignKey(verbose_name='Parent Voucher', to='voucher.Voucher', null=True, blank=True, related_name='children'),
        ),
    ]
