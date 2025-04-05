# Generated by Django 4.2.8 on 2024-05-18 16:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('travel_app', '0003_remove_result_image_filename'),
    ]

    operations = [
        migrations.AddField(
            model_name='destination',
            name='additional_image',
            field=models.ImageField(blank=True, null=True, upload_to='destination_images/'),
        ),
        migrations.AddField(
            model_name='destination',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='destination',
            name='title',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
