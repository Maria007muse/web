import django
import os
import itertools
from travel_app.models import Destination, RelevanceScore
from travel_app.idk.recommendations import get_yandexgpt_relevance

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'holiday_choice_web.settings')
django.setup()


def cache_popular_combinations():
    """Кэширует релевантность для популярных комбинаций фильтров."""
    # Пример популярных фильтров (можно расширить)
    countries = ['Италия', 'Испания', 'Франция', '']
    seasons = ['Лето', 'Зима', '']
    activity_types = ['Горнолыжный', 'Пляжный', 'Культурный', '']
    tags = ['Романтика', 'Активный отдых', '']

    all_destinations = Destination.objects.all()
    for country, season, activity, tag in itertools.product(countries, seasons, activity_types, tags):
        filters = {
            'country': country,
            'season': season,
            'activity_type': activity,
            'tags': tag
        }
        active_filters = {k: v for k, v in filters.items() if v}
        if not active_filters:
            continue
        filters_hash = RelevanceScore.generate_filters_hash(active_filters)
        for dest in all_destinations:
            if not RelevanceScore.objects.filter(destination=dest, filters_hash=filters_hash).exists():
                score = get_yandexgpt_relevance(dest, active_filters)
                RelevanceScore.objects.create(
                    destination=dest,
                    filters_hash=filters_hash,
                    score=score
                )
                print(f"Cached: {dest.recommendation} - {filters} - {score}%")

if __name__ == "__main__":
    cache_popular_combinations()
