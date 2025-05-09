# Generated by Django 4.2.8 on 2024-05-21 12:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('travel_app', '0005_alter_destination_additional_image_review'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='reviews',
            field=models.ManyToManyField(blank=True, related_name='profile_reviews', to='travel_app.review'),
        ),
    ]
