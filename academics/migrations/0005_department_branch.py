# Generated by Django 5.2.3 on 2025-07-06 09:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0004_alter_department_options_remove_department_parent"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="branch",
            field=models.CharField(default=1, max_length=100),
            preserve_default=False,
        ),
    ]
