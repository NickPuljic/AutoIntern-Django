# Generated by Django 2.0.2 on 2018-04-11 00:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autoIntern', '0004_data_rangyselection'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='public',
            field=models.BooleanField(default=True),
        ),
    ]
