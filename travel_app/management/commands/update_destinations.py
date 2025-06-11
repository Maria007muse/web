import csv
from django.core.management.base import BaseCommand
from travel_app.models import Destination, ActivityType, Language, Tag, Vibe, ComfortLevel

class Command(BaseCommand):
    help = 'Обновление и заполнение направлений из CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        with open(csv_file, encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    # Создание или обновление объекта Destination
                    dest, created = Destination.objects.update_or_create(
                        id=row['id'],
                        defaults={
                            'climate': row['climate'],
                            # 'image': row['image'],
                            'recommendation': row['recommendation'],
                            # 'description': row['description'],
                            # 'title': row['title'],
                            # 'country': row['country'],
                            # 'is_popular': row['is_popular'].lower() == 'true',
                            # 'season': row['season'],
                            'family_friendly': row['family_friendly'].lower() == 'true',
                            # 'visa_required': row['visa_required'].lower() == 'true',
                        }
                    )

                    # Обработка ManyToMany полей
                    # ActivityType
                    if row.get('activity_type'):
                        activity_types = [x.strip() for x in row['activity_type'].split(',') if x.strip()]
                        dest.activity_types.clear()
                        for activity in activity_types:
                            obj, _ = ActivityType.objects.get_or_create(name=activity)
                            dest.activity_types.add(obj)

                    # Language
                    if row.get('language'):
                        languages = [x.strip() for x in row['language'].split(',') if x.strip()]
                        dest.language.clear()
                        for lang in languages:
                            obj, _ = Language.objects.get_or_create(name=lang)
                            dest.language.add(obj)

                    # Tag
                    if row.get('tags'):
                        tags = [x.strip() for x in row['tags'].split(',') if x.strip()]
                        dest.tags.clear()
                        for tag in tags:
                            obj, _ = Tag.objects.get_or_create(name=tag)
                            dest.tags.add(obj)

                    # Vibe
                    if row.get('vibe'):
                        vibes = [x.strip() for x in row['vibe'].split(',') if x.strip()]
                        dest.vibe.clear()
                        for vibe in vibes:
                            obj, _ = Vibe.objects.get_or_create(name=vibe)
                            dest.vibe.add(obj)

                    # ComfortLevel
                    if row.get('comfort_level'):
                        comfort_levels = [x.strip() for x in row['comfort_level'].split(',') if x.strip()]
                        dest.comfort_level.clear()
                        for comfort in comfort_levels:
                            obj, _ = ComfortLevel.objects.get_or_create(name=comfort)
                            dest.comfort_level.add(obj)

                    dest.save()
                    self.stdout.write(self.style.SUCCESS(f'{"Создано" if created else "Обновлено"}: {dest.recommendation}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Ошибка в ID {row["id"]}: {str(e)}'))
