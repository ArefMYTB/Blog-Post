# Generated by Django 5.0.6 on 2024-07-08 08:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="blogpost",
            name="numScore",
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]
