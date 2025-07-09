from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("basket", "0005_auto_20150604_1450"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="line",
            options={
                "ordering": ["date_created", "pk"],
                "verbose_name": "Basket line",
                "verbose_name_plural": "Basket lines",
            },
        ),
    ]
