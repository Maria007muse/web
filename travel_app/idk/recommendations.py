import logging
import numpy as np
import faiss
from django.db.models import Q, Avg
from sentence_transformers import SentenceTransformer
from travel_app.models import Destination

logger = logging.getLogger(__name__)

def get_filtered_destinations(filters, sort_by='relevance'):
    active_filters = {k: v for k, v in filters.items() if v or isinstance(v, bool)}
    total_filters = len(active_filters)
    if not total_filters:
        return []

    logger.debug(f"Активные фильтры для Q-запроса: {active_filters}")

    # Шаг 1: Точное совпадение (100%)
    query = Q()
    for key, value in active_filters.items():
        if key == 'tags' and value:
            for tag in value.split(','):
                query &= Q(tags__contains=tag.strip())
        elif key in ['budget_min', 'budget_max']:
            continue
        elif key in ['family_friendly', 'visa_required']:
            query &= Q(**{key: value})
        elif value:
            query &= Q(**{f"{key}__iexact" if key == 'country' else key: value})

    if 'budget_min' in active_filters and 'budget_max' in active_filters:
        query &= Q(budget_min__lte=active_filters['budget_max'], budget_max__gte=active_filters['budget_min'])
    elif 'budget_min' in active_filters:
        query &= Q(budget_max__gte=active_filters['budget_min'])
    elif 'budget_max' in active_filters:
        query &= Q(budget_min__lte=active_filters['budget_max'])

    exact_matches = Destination.objects.filter(query)
    logger.debug(f"Точные совпадения: {exact_matches.count()} направлений, IDs: {[d.id for d in exact_matches]}")

    ratings = {dest.id: dest.reviews.aggregate(Avg('rating'))['rating__avg'] or 0 for dest in Destination.objects.all()}
    destinations = [
        {
            'destination': dest,
            'score_percentage': 100.0,
            'is_popular': dest.is_popular,
            'is_recommended': False,
            'rating_avg': ratings.get(dest.id, 0)
        } for dest in exact_matches
    ]

    # Шаг 2: Векторный поиск для частичных совпадений
    exclude_ids = [d['destination'].id for d in destinations]
    max_destinations = 10 if exact_matches.count() > 1 else 8

    # Подготовка запроса для эмбеддинга
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_text = " ".join([f"{k.replace('_', ' ')} {str(v).lower()}" for k, v in active_filters.items() if v not in [None, '']])

    query_embedding = model.encode(query_text, convert_to_numpy=True)

    # Загрузка всех эмбеддингов из базы
    all_destinations = Destination.objects.exclude(embedding__isnull=True).exclude(id__in=exclude_ids)
    if not all_destinations:
        return destinations

    embeddings = np.array([dest.embedding for dest in all_destinations], dtype=np.float32)
    dest_ids = [dest.id for dest in all_destinations]

    # Инициализация Faiss
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Косинусное сходство
    faiss.normalize_L2(embeddings)  # Нормализация
    index.add(embeddings)

    # Поиск ближайших
    k = min(10, len(all_destinations))  # Топ-10 кандидатов
    query_embedding = query_embedding.reshape(1, -1)
    faiss.normalize_L2(query_embedding)
    distances, indices = index.search(query_embedding, k)

    # Фильтрация результатов
    partial_matches = []
    for idx, distance in zip(indices[0], distances[0]):
        dest = all_destinations[int(idx)]  # Приводим idx к int
        score = distance * 100  # Косинусное сходство в проценты
        # Штраф за противоположные сезоны
        if 'season' in active_filters:
            season = active_filters['season']
            if (season == 'Зима' and dest.season == 'Лето') or (season == 'Лето' and dest.season == 'Зима') or \
               (season == 'Весна' and dest.season == 'Осень') or (season == 'Осень' and dest.season == 'Весна'):
                score *= 0.7
        # Штраф за несовпадение activity_type
        if 'activity_type' in active_filters and dest.activity_type.lower() != active_filters['activity_type'].lower():
            score *= 0.8
        # Штраф за несовпадение страны
        if 'country' in active_filters and dest.country.lower() != active_filters['country'].lower():
            score *= 0.8
        partial_matches.append({
            'destination': dest,
            'score_percentage': min(round(score, 1), 99.9),
            'is_popular': dest.is_popular,
            'is_recommended': True,
            'rating_avg': ratings.get(dest.id, 0)
        })

    destinations.extend(partial_matches[:max_destinations - len(destinations)])

    # Шаг 3: Сортировка
    if destinations:
        if sort_by == 'relevance':
            destinations.sort(key=lambda x: (-x['score_percentage'], -x['rating_avg']))
        elif sort_by == 'rating':
            destinations.sort(key=lambda x: (-x['rating_avg'], -x['score_percentage']))
        elif sort_by == 'budget_asc':
            destinations.sort(key=lambda x: (-x['score_percentage'], x['destination'].budget_min or float('inf')))
        elif sort_by == 'budget_desc':
            destinations.sort(key=lambda x: (-x['score_percentage'], -(x['destination'].budget_max or 0)))
        elif sort_by == 'popularity':
            destinations.sort(key=lambda x: (-x['score_percentage'], -x['destination'].is_popular))

    logger.debug(f"Найдено {len(destinations)} направлений с фильтрами: {active_filters}")
    return destinations
