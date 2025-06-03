from django.db import migrations


def migrate_activity_types(apps, schema_editor):
    Destination = apps.get_model('travel_app', 'Destination')
    ActivityType = apps.get_model('travel_app', 'ActivityType')

    # Явно определяем ACTIVITY_CHOICES внутри миграции
    ACTIVITY_CHOICES = [
        ("Горнолыжный", "Горнолыжный"),
        ("Культурный", "Культурный"),
        ("Пляжный", "Пляжный"),
        ("Гастрономический", "Гастрономический"),
        ("Экотуризм", "Экотуризм"),
        ("Шопинг", "Шопинг"),
        ("Приключенческий", "Приключенческий"),
    ]

    # Создаём записи для всех возможных активностей
    for choice in ACTIVITY_CHOICES:
        ActivityType.objects.get_or_create(name=choice[0])

    # Переносим данные из activity_type в activity_types
    for dest in Destination.objects.all():
        if dest.activity_type:  # Если поле не пустое
            activity, _ = ActivityType.objects.get_or_create(name=dest.activity_type)
            dest.activity_types.add(activity)


def reverse_migrate_activity_types(apps, schema_editor):
    Destination = apps.get_model('travel_app', 'Destination')
    for dest in Destination.objects.all():
        activities = dest.activity_types.all()
        if activities:
            dest.activity_type = activities[0].name
            dest.save()


class Migration(migrations.Migration):
    dependencies = [
        ('travel_app', '0015_activitytype_alter_destination_language_and_more'),
    ]
    operations = [
        migrations.RunPython(migrate_activity_types, reverse_migrate_activity_types),
    ]
