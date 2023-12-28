# Generated by Django 4.2.8 on 2023-12-26 21:08

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Destination',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('climate', models.CharField(choices=[('Умеренный', 'Умеренный'), ('Холодный', 'Холодный'), ('Теплый', 'Теплый')], max_length=30)),
                ('activity_type', models.CharField(choices=[('Горнолыжный', 'Горнолыжный'), ('Культурный', 'Культурный'), ('Пляжный', 'Пляжный')], max_length=30)),
                ('budget', models.CharField(choices=[('От 300000 руб', 'От 300000 руб'), ('От 100000 до 300000 руб', 'От 100000 до 300000 руб'), ('До 100000 руб', 'До 100000 руб')], max_length=30)),
                ('popularity', models.CharField(choices=[('Низкая', 'Низкая'), ('Высокая', 'Высокая')], max_length=30)),
                ('cultural_diversity', models.CharField(choices=[('Большое', 'Большое'), ('Умеренное', 'Умеренное'), ('Незначительное', 'Незначительное')], max_length=30)),
                ('image', models.ImageField(upload_to='destination_images/')),
            ],
        ),
        migrations.CreateModel(
            name='Recommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('image', models.ImageField(upload_to='recommendation_images/')),
            ],
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recommendation', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='travel_app.recommendation')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('results', models.ManyToManyField(blank=True, to='travel_app.result')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
