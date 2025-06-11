import random
from collections import Counter

import numpy as np
from django.contrib.auth.models import User
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import Destination, UserInteraction, InspirationPost
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

def get_filtered_destinations(request, form):
    destinations = []
    message = None
    page_obj = None

    if not form.is_valid():
        logger.error("Форма невалидна: %s", form.errors)
        return destinations, message, page_obj

    filters = {
        'country': form.cleaned_data['country'].strip().lower() if form.cleaned_data['country'] else '',
        'climate': form.cleaned_data['climate'],
        'activity_types': form.cleaned_data['activity_types'],
        'season': form.cleaned_data['season'],
        'vibe': form.cleaned_data['vibe'],
        'comfort_level': form.cleaned_data['comfort_level'],
        'family_friendly': form.cleaned_data['family_friendly'],
        'visa_required': form.cleaned_data['visa_required'],
        'language': form.cleaned_data['language'],
        'tags': form.cleaned_data['tags'],
        'sort_by': form.cleaned_data.get('sort_by') or 'relevance'
    }

    filters_provided = any(
        (isinstance(v, list) and len(v) > 0) or
        (isinstance(v, bool) and v) or
        (isinstance(v, str) and v)
        for v in filters.values() if v is not None
    )
    if not filters_provided:
        message = "Выберите хотя бы один фильтр."
        return destinations, message, page_obj

    q = Q()

    if filters['country']:
        q &= Q(country__icontains=filters['country'])

    for field in ('climate', 'season'):
        vals = filters.get(field)
        if vals:
            sub_q = Q()
            for val in vals:
                sub_q |= Q(**{f"{field}__icontains": val})
            q &= sub_q

    for field in ('activity_types', 'language', 'tags', 'vibe', 'comfort_level'):
        vals = filters.get(field)
        if vals:
            sub_q = Q()
            for val in vals:
                sub_q |= Q(**{f"{field}__name": val})
            q &= sub_q

    if filters['family_friendly']:
        q &= Q(family_friendly=True)
    if filters['visa_required']:
        q &= Q(visa_required=True)

    destinations_qs = Destination.objects.filter(q).distinct()

    if not destinations_qs.exists():
        message = "Мест, соответствующих фильтрам, не найдено."

    for dest in destinations_qs:
        score = 0
        if filters['climate']:
            score += sum(1 for val in filters['climate'] if val in (dest.climate or ""))
        if filters['activity_types']:
            dest_activities = list(dest.activity_types.values_list('name', flat=True))
            score += sum(1 for val in filters['activity_types'] if val in dest_activities)
        if filters['tags']:
            dest_tags = list(dest.tags.values_list('name', flat=True))
            score += sum(1 for tag in filters['tags'] if tag in dest_tags)
        if filters['vibe']:
            dest_vibes = list(dest.vibe.values_list('name', flat=True))
            score += sum(1 for val in filters['vibe'] if val in dest_vibes)
        if filters['comfort_level']:
            dest_comfort = list(dest.comfort_level.values_list('name', flat=True))
            score += sum(1 for val in filters['comfort_level'] if val in dest_comfort)
        destinations.append({
            'destination': dest,
            'score': score,
            'score_percentage': (score / (len(filters['climate']) + len(filters['activity_types']) + len(filters['tags']) + len(filters['vibe']) + len(filters['comfort_level']) or 1)) * 100,
            'is_popular': dest.is_popular,
            'is_recommended': False
        })

    sort_by = filters['sort_by']
    if destinations and sort_by != 'relevance':
        if sort_by == 'rating':
            destinations.sort(
                key=lambda x: x['destination'].reviews.aggregate(Avg('rating'))['rating__avg'] or 0,
                reverse=True
            )
        elif sort_by == 'popularity':
            destinations.sort(key=lambda x: x['destination'].is_popular, reverse=True)
    else:
        destinations.sort(key=lambda x: x['score'], reverse=True)

    if request.user.is_authenticated:
        UserInteraction.objects.create(
            user=request.user,
            destination=None,
            interaction_type='search',
            search_filters=filters
        )

    paginator = Paginator(destinations, 8)
    page_obj = paginator.get_page(request.GET.get('page'))

    return destinations, message, page_obj

def calculate_similarity(dest, filters, weights):
    score = 0
    if filters.get('country') and dest.country.lower() == filters.get('country').lower():
        score += weights['country']
    if filters.get('climate') and dest.climate in filters.get('climate'):
        score += weights['climate']
    if filters.get('activity_types'):
        dest_activities = list(dest.activity_types.values_list('name', flat=True))
        if any(activity in filters.get('activity_types') for activity in dest_activities):
            score += weights['activity_types']
    if filters.get('season') and dest.season in filters.get('season'):
        score += weights['season']
    if filters.get('vibe'):
        dest_vibes = list(dest.vibe.values_list('name', flat=True))
        if any(vibe in filters.get('vibe') for vibe in dest_vibes):
            score += weights['vibe']
    if filters.get('comfort_level'):
        dest_comfort = list(dest.comfort_level.values_list('name', flat=True))
        if any(comfort in filters.get('comfort_level') for comfort in dest_comfort):
            score += weights['comfort_level']
    if filters.get('language'):
        dest_languages = list(dest.language.values_list('name', flat=True))
        if any(lang in filters.get('language') for lang in dest_languages):
            score += weights['language']
    if filters.get('family_friendly') and dest.family_friendly == filters.get('family_friendly'):
        score += weights['family_friendly']
    if filters.get('visa_required') is not None and dest.visa_required == filters.get('visa_required'):
        score += weights['visa_required']
    if filters.get('tags'):
        dest_tags = list(dest.tags.values_list('name', flat=True))
        matching_tags = len(set(filters['tags']) & set(dest_tags))
        if matching_tags > 0:
            score += weights['tags'] * (matching_tags / len(filters['tags']))
    return score

def get_user_behavior_recommendations(user, filters, exclude_destination_ids, limit=4):
    if not filters:
        logger.debug("Фильтры пусты, возвращаем популярные рекомендации")
        return get_popular_recommendations(exclude_destination_ids, limit)

    recommendations = []
    weights = {
        'country': 30,
        'climate': 15,
        'activity_types': 15,
        'season': 10,
        'vibe': 5,
        'comfort_level': 5,
        'family_friendly': 5,
        'visa_required': 5,
        'language': 5,
        'tags': 10,
    }
    max_score = sum(weights.values())

    if user.is_authenticated:
        interactions = UserInteraction.objects.filter(user=user).order_by('-created_at')[:10]
        user_filters = []
        interacted_destinations = []
        for inter in interactions:
            if inter.interaction_type == 'search' and inter.search_filters:
                user_filters.append(inter.search_filters)
            if inter.destination:
                interacted_destinations.append(inter.destination)

        for dest in interacted_destinations:
            if dest.id not in exclude_destination_ids:
                score = calculate_similarity(dest, filters, weights)
                if score > 0:
                    recommendations.append({
                        'destination': dest,
                        'score': score + 10,
                        'score_percentage': ((score + 10) / (max_score + 10)) * 100,
                        'is_popular': dest.is_popular,
                        'is_recommended': True
                    })
                    logger.debug(
                        f"Добавлено взаимодействованное место: {dest.recommendation}, "
                        f"score={score + 10}, "
                        f"причина: совпадение с фильтрами {filters}"
                    )

    if filters.get('country'):
        candidates = Destination.objects.filter(country__iexact=filters['country']).exclude(
            id__in=exclude_destination_ids)
        for dest in candidates:
            if dest.id not in [r['destination'].id for r in recommendations]:
                score = calculate_similarity(dest, filters, weights)
                score += weights['country'] * 0.5
                if score > 0:
                    recommendations.append({
                        'destination': dest,
                        'score': score,
                        'score_percentage': (score / max_score) * 100,
                        'is_popular': dest.is_popular,
                        'is_recommended': True
                    })
                    logger.debug(
                        f"Добавлено по стране {filters['country']}: {dest.recommendation}, "
                        f"score={score}, "
                        f"причина: совпадение с фильтрами {filters}"
                    )

    if len(recommendations) < limit:
        remaining = limit - len(recommendations)
        exclude_ids = set(exclude_destination_ids) | {r['destination'].id for r in recommendations}
        other_candidates = Destination.objects.exclude(id__in=exclude_ids)
        if filters.get('country'):
            other_candidates = other_candidates.exclude(country__iexact=filters['country'])
        for dest in other_candidates:
            score = calculate_similarity(dest, filters, weights)
            if score > 0:
                recommendations.append({
                    'destination': dest,
                    'score': score,
                    'score_percentage': (score / max_score) * 100,
                    'is_popular': dest.is_popular,
                    'is_recommended': True
                })
                logger.debug(
                    f"Добавлено дополнительное место: {dest.recommendation}, "
                    f"score={score}, "
                    f"причина: совпадение с фильтрами {filters}"
                )

    if len(recommendations) < limit:
        remaining = limit - len(recommendations)
        exclude_ids = set(exclude_destination_ids) | {r['destination'].id for r in recommendations}
        popular_recs = get_popular_recommendations(exclude_ids, remaining)
        recommendations.extend(popular_recs)
        for rec in popular_recs:
            logger.debug(
                f"Добавлено популярное место: {rec['destination'].recommendation}, "
                f"score={rec['score']}, "
                f"причина: популярное, не взаимодействовал"
            )

    recommendations.sort(key=lambda x: x['score'], reverse=True)
    logger.debug(f"Итоговые рекомендации: {[r['destination'].recommendation for r in recommendations]}")
    return recommendations[:limit]

def get_popular_recommendations(exclude_destination_ids, limit=4):
    recommendations = []
    popular = Destination.objects.filter(is_popular=True).exclude(id__in=exclude_destination_ids)[:limit]
    for dest in popular:
        recommendations.append({
            'destination': dest,
            'score': 0,
            'score_percentage': 0,
            'is_popular': True,
            'is_recommended': True
        })
    return recommendations

def get_personalized_recommendations(user, exclude_destination_ids, limit=4):
    recommendations = []
    if user.is_authenticated:
        interactions = UserInteraction.objects.filter(user=user).order_by('-created_at')
        seen_ids = set(inter.destination.id for inter in interactions if inter.destination)
        seen_ids.update(exclude_destination_ids)

        # 1. Последний поиск
        search_inter = interactions.filter(interaction_type='search').first()
        if search_inter and search_inter.search_filters:
            logger.debug(f"Найден последний поиск для {user.username}: {search_inter.search_filters}")
            recs = get_user_behavior_recommendations(user, search_inter.search_filters, seen_ids, limit)
            recommendations.extend(recs)
            for rec in recs:
                logger.debug(
                    f"Добавлено по последнему поиску: {rec['destination'].recommendation}, "
                    f"score={rec['score']}, "
                    f"причина: похож на фильтры поиска {search_inter.search_filters}"
                )

        # 2. Избранное
        if len(recommendations) < limit:
            favorite_inter = interactions.filter(interaction_type='favorite')
            for inter in favorite_inter[:2]:
                if inter.destination:
                    dest_filters = {
                        'country': inter.destination.country,
                        'climate': [inter.destination.climate] if inter.destination.climate else [],
                        'activity_types': list(inter.destination.activity_types.values_list('name', flat=True)),
                        'season': [inter.destination.season] if inter.destination.season else [],
                        'vibe': list(inter.destination.vibe.values_list('name', flat=True)),
                        'comfort_level': list(inter.destination.comfort_level.values_list('name', flat=True)),
                        'family_friendly': inter.destination.family_friendly,
                        'visa_required': inter.destination.visa_required,
                        'language': list(inter.destination.language.values_list('name', flat=True)),
                        'tags': list(inter.destination.tags.values_list('name', flat=True))
                    }
                    recs = get_user_behavior_recommendations(user, dest_filters, seen_ids, limit - len(recommendations))
                    recommendations.extend(recs)
                    for rec in recs:
                        logger.debug(
                            f"Добавлено по избранному: {rec['destination'].recommendation}, "
                            f"score={rec['score']}, "
                            f"причина: похож на избранное {inter.destination.recommendation}"
                        )

        # 3. Просмотры
        if len(recommendations) < limit:
            view_inter = interactions.filter(interaction_type='view')
            for inter in view_inter[:2]:
                if inter.destination:
                    dest_filters = {
                        'country': inter.destination.country,
                        'climate': [inter.destination.climate] if inter.destination.climate else [],
                        'activity_types': list(inter.destination.activity_types.values_list('name', flat=True)),
                        'season': [inter.destination.season] if inter.destination.season else [],
                        'vibe': list(inter.destination.vibe.values_list('name', flat=True)),
                        'comfort_level': list(inter.destination.comfort_level.values_list('name', flat=True)),
                        'family_friendly': inter.destination.family_friendly,
                        'visa_required': inter.destination.visa_required,
                        'language': list(inter.destination.language.values_list('name', flat=True)),
                        'tags': list(inter.destination.tags.values_list('name', flat=True))
                    }
                    recs = get_user_behavior_recommendations(user, dest_filters, seen_ids, limit - len(recommendations))
                    recommendations.extend(recs)
                    for rec in recs:
                        logger.debug(
                            f"Добавлено по просмотрам: {rec['destination'].recommendation}, "
                            f"score={rec['score']}, "
                            f"причина: похож на просмотренное {inter.destination.recommendation}"
                        )

        # 4. Отзывы
        if len(recommendations) < limit:
            review_inter = interactions.filter(interaction_type='review')
            for inter in review_inter[:2]:
                if inter.destination:
                    dest_filters = {
                        'country': inter.destination.country,
                        'climate': [inter.destination.climate] if inter.destination.climate else [],
                        'activity_types': list(inter.destination.activity_types.values_list('name', flat=True)),
                        'season': [inter.destination.season] if inter.destination.season else [],
                        'vibe': list(inter.destination.vibe.values_list('name', flat=True)),
                        'comfort_level': list(inter.destination.comfort_level.values_list('name', flat=True)),
                        'family_friendly': inter.destination.family_friendly,
                        'visa_required': inter.destination.visa_required,
                        'language': list(inter.destination.language.values_list('name', flat=True)),
                        'tags': list(inter.destination.tags.values_list('name', flat=True))
                    }
                    recs = get_user_behavior_recommendations(user, dest_filters, seen_ids, limit - len(recommendations))
                    recommendations.extend(recs)
                    for rec in recs:
                        logger.debug(
                            f"Добавлено по отзывам: {rec['destination'].recommendation}, "
                            f"score={rec['score']}, "
                            f"причина: похож на место с отзывом {inter.destination.recommendation}"
                        )

    if len(recommendations) < limit:
        seen_ids = set(inter.destination.id for inter in UserInteraction.objects.filter(user=user) if inter.destination) if user.is_authenticated else set()
        seen_ids.update(exclude_destination_ids)
        popular_recs = get_popular_recommendations(seen_ids, limit - len(recommendations))
        recommendations.extend(popular_recs)
        for rec in popular_recs:
            logger.debug(
                f"Добавлено по популярности: {rec['destination'].recommendation}, "
                f"score={rec['score']}, "
                f"причина: популярное место, не взаимодействовал"
            )

    recommendations.sort(key=lambda x: x['score'], reverse=True)
    return recommendations[:limit]

def _get_current_season():
    month = timezone.now().month
    if month in [12, 1, 2]:
        return 'Зима'
    elif month in [3, 4, 5]:
        return 'Весна'
    elif month in [6, 7, 8]:
        return 'Лето'
    else:
        return 'Осень'


def get_seasonal_recommendations(limit=4):
    season = _get_current_season()
    destinations = Destination.objects.filter(season__icontains=season).order_by('-is_popular')[:limit]
    return destinations


def get_seasonal_personal_recommendations(user, limit=6):
    current_season = _get_current_season()

    logger.debug(
        f"Формирование персонализированных сезонных рекомендаций для пользователя {user.username if user.is_authenticated else 'аноним'}, сезон: {current_season}")

    q = Q(season__icontains=current_season)

    if user.is_authenticated:
        interests = {
            'climate': set(),
            'activity_types': set(),
        }
        logger.debug(f"Сбор интересов пользователя {user.username}")
        interactions = UserInteraction.objects.filter(user=user).order_by('-created_at')[:10]
        if not interactions:
            logger.debug(f"У пользователя {user.username} нет взаимодействий, возвращаем общие сезонные рекомендации")

        for inter in interactions:
            if inter.search_filters:
                logger.debug(f"Анализ поисковых фильтров: {inter.search_filters}")
                for key in interests.keys():
                    val = inter.search_filters.get(key)
                    if val:
                        if isinstance(val, list):
                            interests[key].update(val)
                        else:
                            interests[key].add(val)

        if interests['climate']:
            logger.debug(f"Интересы по климату: {interests['climate']}")
            sub_q = Q()
            for climate in interests['climate']:
                sub_q |= Q(climate__icontains=climate)
            q &= sub_q

        if interests['activity_types']:
            logger.debug(f"Интересы по активностям: {interests['activity_types']}")
            sub_q = Q()
            for act in interests['activity_types']:
                sub_q |= Q(activity_types__name=act)
            q &= sub_q

    destinations = Destination.objects.filter(q).distinct()
    logger.debug(f"Найдено мест по фильтрам: {destinations.count()}")

    destinations = destinations.order_by('-is_popular')[:limit]
    logger.debug(f"Итоговые персонализированные сезонные рекомендации: {[d.recommendation for d in destinations]}")

    return destinations

def get_inspiration_recommendations(user, limit=4):
    logger.debug(f"Формирование подборки для вдохновения для пользователя {user.username if user.is_authenticated else 'аноним'}")
    recommendations = []
    seen_ids = set()

    if user.is_authenticated:
        interactions = UserInteraction.objects.filter(user=user).order_by('-created_at')
        seen_ids = set(inter.destination.id for inter in interactions if inter.destination)
        logger.debug(f"Исключенные ID (просмотренные): {seen_ids}")

        # 1. Собираем фильтры из избранного
        favorite_filters = {
            'tags': set(),
            'vibe': set(),
            'climate': set(),
            'activity_types': set(),
            'season': set()
        }
        favorites = interactions.filter(interaction_type='favorite')[:10]
        for inter in favorites:
            if inter.destination:
                favorite_filters['tags'].update(inter.destination.tags.values_list('name', flat=True))
                favorite_filters['vibe'].update(inter.destination.vibe.values_list('name', flat=True))
                favorite_filters['climate'].add(inter.destination.climate)
                favorite_filters['activity_types'].update(inter.destination.activity_types.values_list('name', flat=True))
                favorite_filters['season'].add(inter.destination.season)
        logger.debug(f"Фильтры из избранного: {favorite_filters}")

        # 2. Собираем фильтры из поисков
        search_filters = {
            'tags': set(),
            'vibe': set(),
            'climate': set(),
            'activity_types': set(),
            'season': set()
        }
        searches = interactions.filter(interaction_type='search')[:10]
        for inter in searches:
            if inter.search_filters:
                for key in search_filters.keys():
                    val = inter.search_filters.get(key)
                    if val:
                        if isinstance(val, list):
                            search_filters[key].update(val)
                        else:
                            search_filters[key].add(val)
        logger.debug(f"Фильтры из поисков: {search_filters}")

        # 3. Объединяем фильтры (60–80% совпадение)
        combined_filters = {
            'tags': set(random.sample(list(favorite_filters['tags']) + list(search_filters['tags']),
                                     k=min(len(favorite_filters['tags']) + len(search_filters['tags']),
                                           int(0.8 * (len(favorite_filters['tags']) + len(search_filters['tags'])) or 1)))),
            'vibe': set(random.sample(list(favorite_filters['vibe']) + list(search_filters['vibe']),
                                     k=min(len(favorite_filters['vibe']) + len(search_filters['vibe']),
                                           int(0.8 * (len(favorite_filters['vibe']) + len(search_filters['vibe'])) or 1)))),
            'climate': set(random.sample(list(favorite_filters['climate']) + list(search_filters['climate']),
                                       k=min(len(favorite_filters['climate']) + len(search_filters['climate']),
                                             int(0.7 * (len(favorite_filters['climate']) + len(search_filters['climate'])) or 1)))),
            'activity_types': set(random.sample(list(favorite_filters['activity_types']) + list(search_filters['activity_types']),
                                               k=min(len(favorite_filters['activity_types']) + len(search_filters['activity_types']),
                                                     int(0.7 * (len(favorite_filters['activity_types']) + len(search_filters['activity_types'])) or 1)))),
            'season': set(random.sample(list(favorite_filters['season']) + list(search_filters['season']),
                                       k=min(len(favorite_filters['season']) + len(search_filters['season']),
                                             int(0.7 * (len(favorite_filters['season']) + len(search_filters['season'])) or 1))))
        }
        logger.debug(f"Комбинированные фильтры (60–80% совпадение): {combined_filters}")

        # 4. Формируем запрос
        q = Q()
        if combined_filters['tags']:
            sub_q = Q()
            for tag in combined_filters['tags']:
                sub_q |= Q(tags__name=tag)
            q &= sub_q
        if combined_filters['vibe']:
            sub_q = Q()
            for vibe in combined_filters['vibe']:
                sub_q |= Q(vibe__name=vibe)
            q &= sub_q
        if combined_filters['climate']:
            sub_q = Q()
            for climate in combined_filters['climate']:
                sub_q |= Q(climate__icontains=climate)
            q &= sub_q
        if combined_filters['activity_types']:
            sub_q = Q()
            for act in combined_filters['activity_types']:
                sub_q |= Q(activity_types__name=act)
            q &= sub_q
        if combined_filters['season']:
            sub_q = Q()
            for season in combined_filters['season']:
                sub_q |= Q(season__icontains=season)
            q &= sub_q

        destinations = Destination.objects.filter(q).exclude(id__in=seen_ids).distinct()
        logger.debug(f"Найдено мест по комбинированным фильтрам: {destinations.count()}")

        # 5. Сортировка и выбор
        weights = {'tags': 0.4, 'vibe': 0.3, 'climate': 0.15, 'activity_types': 0.1, 'season': 0.05}
        for dest in destinations:
            score = sum([
                weights['tags'] * len(set(combined_filters['tags']) & set(dest.tags.values_list('name', flat=True))),
                weights['vibe'] * len(set(combined_filters['vibe']) & set(dest.vibe.values_list('name', flat=True))),
                weights['climate'] * (1 if dest.climate in combined_filters['climate'] else 0),
                weights['activity_types'] * len(set(combined_filters['activity_types']) & set(dest.activity_types.values_list('name', flat=True))),
                weights['season'] * (1 if dest.season in combined_filters['season'] else 0)
            ])
            recommendations.append({
                'destination': dest,
                'score': score,
                'score_percentage': (score / sum(weights.values())) * 100,
                'is_popular': dest.is_popular,
                'is_recommended': True
            })
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        recommendations = recommendations[:limit]
        logger.debug(f"Итоговые рекомендации для вдохновения: {[r['destination'].recommendation for r in recommendations]}")

    # Fallback: популярные места, если нет данных
    if len(recommendations) < limit:
        remaining = limit - len(recommendations)
        popular_recs = get_popular_recommendations(seen_ids, remaining)
        recommendations.extend(popular_recs)
        logger.debug(f"Добавлены популярные места (fallback): {[r['destination'].recommendation for r in popular_recs]}")

    return recommendations


def get_trending_recommendations(limit=4):
    logger.debug("Формирование блока 'Популярное сейчас'")
    recommendations = []

    # Период для актуальности: последние 30 дней
    time_threshold = timezone.now() - timedelta(days=30)
    logger.debug(f"Учитываются взаимодействия с {time_threshold}")

    # Подсчет взаимодействий по типам с весами
    interactions = UserInteraction.objects.filter(
        created_at__gte=time_threshold,
        destination__isnull=False
    ).values('destination').annotate(
        view_count=Count('id', filter=Q(interaction_type='view')),
        favorite_count=Count('id', filter=Q(interaction_type='favorite')),
        review_count=Count('id', filter=Q(interaction_type='review')),
        total_score=Count('id', filter=Q(interaction_type='view')) * 1 +
                    Count('id', filter=Q(interaction_type='favorite')) * 2 +
                    Count('id', filter=Q(interaction_type='review')) * 3
    ).order_by('-total_score')[:limit]

    logger.debug(f"Найдено мест с взаимодействиями: {len(interactions)}")

    for inter in interactions:
        dest = Destination.objects.get(id=inter['destination'])
        recommendations.append({
            'destination': dest,
            'score': inter['total_score'],
            'score_percentage': (inter['total_score'] / (limit * 10)) * 100,
            'is_popular': dest.is_popular,
            'is_recommended': True
        })
        logger.debug(
            f"Добавлено место: {dest.recommendation}, "
            f"score={inter['total_score']} "
            f"(views={inter['view_count']}, favorites={inter['favorite_count']}, reviews={inter['review_count']})"
        )

    # Fallback: если взаимодействий мало, добавляем популярные места
    if len(recommendations) < limit:
        remaining = limit - len(recommendations)
        seen_ids = {rec['destination'].id for rec in recommendations}
        popular = Destination.objects.filter(is_popular=True).exclude(id__in=seen_ids)
        popular = list(popular)[:remaining]
        random.shuffle(popular)
        for dest in popular:
            recommendations.append({
                'destination': dest,
                'score': 0,
                'score_percentage': 0,
                'is_popular': True,
                'is_recommended': True
            })
            logger.debug(f"Добавлено популярное место (fallback): {dest.recommendation}")

    logger.debug(f"Итоговые трендовые рекомендации: {[r['destination'].recommendation for r in recommendations]}")
    return recommendations[:limit]


# rec.py
def get_similar_users_recommendations(user, exclude_destination_ids, limit=4):
    logger.debug(f"Формирование гибридных рекомендаций для {user.username if user.is_authenticated else 'аноним'}")

    if not user.is_authenticated:
        logger.debug("Пользователь не авторизован, возвращаем популярные рекомендации")
        return get_popular_recommendations(exclude_destination_ids, limit)

    recommendations = []
    seen_ids = set(exclude_destination_ids)

    # Собираем профиль пользователя
    user_interactions = UserInteraction.objects.filter(user=user).order_by('-created_at')[:20]
    user_destinations = set(inter.destination.id for inter in user_interactions if inter.destination)
    seen_ids.update(user_destinations)

    user_profile = []
    for inter in user_interactions:
        if inter.search_filters:
            for key in ['country', 'climate', 'season']:
                if inter.search_filters.get(key):
                    val = inter.search_filters[key]
                    user_profile.append(val.lower() if isinstance(val, str) else ' '.join(v.lower() for v in val))
            for key in ['tags', 'vibe']:
                if inter.search_filters.get(key):
                    user_profile.extend(v.lower() for v in inter.search_filters[key])
        if inter.destination:
            user_profile.append(inter.destination.country.lower())
            user_profile.append(inter.destination.climate.lower())
            user_profile.append(inter.destination.season.lower())
            user_profile.extend(v.lower() for v in inter.destination.tags.values_list('name', flat=True))
            user_profile.extend(v.lower() for v in inter.destination.vibe.values_list('name', flat=True))
        if inter.post and inter.post_filters:  # Учитываем теги и атмосферу из постов
            user_profile.extend(v.lower() for v in inter.post_filters.get('tags', []))
            user_profile.extend(v.lower() for v in inter.post_filters.get('vibe', []))

    # Ограничиваем профиль топ-5 тегами
    tag_counts = Counter(user_profile)
    user_profile = set(tag for tag, _ in tag_counts.most_common(5))
    user_profile_text = ' '.join(user_profile)
    logger.debug(f"Профиль пользователя (топ-5 тегов): {user_profile_text}")

    # Векторизация мест
    destinations = Destination.objects.exclude(id__in=seen_ids)
    destination_texts = []
    destination_ids = []
    for dest in destinations:
        text = (
            f"{dest.country.lower()} {dest.climate.lower()} {dest.season.lower()} "
            f"{' '.join(v.lower() for v in dest.tags.values_list('name', flat=True))} "
            f"{' '.join(v.lower() for v in dest.vibe.values_list('name', flat=True))}"
        )
        destination_texts.append(text)
        destination_ids.append(dest.id)

    if not destination_texts:
        logger.debug("Нет доступных мест для рекомендаций, возвращаем популярные")
        return get_popular_recommendations(seen_ids, limit)

    # TF-IDF и косинусное сходство
    vectorizer = TfidfVectorizer()
    dest_vectors = vectorizer.fit_transform(destination_texts)
    user_vector = vectorizer.transform([user_profile_text])
    content_scores = cosine_similarity(user_vector, dest_vectors).flatten()

    content_recommendations = []
    for idx, score in enumerate(content_scores):
        if score > 0:
            dest = Destination.objects.get(id=destination_ids[idx])
            dest_tags = set(v.lower() for v in dest.tags.values_list('name', flat=True))
            dest_vibes = set(v.lower() for v in dest.vibe.values_list('name', flat=True))
            common_attributes = (dest_tags | dest_vibes) & user_profile
            content_recommendations.append({
                'destination': dest,
                'score': score * 100,
                'score_percentage': score * 100,
                'is_popular': dest.is_popular,
                'is_recommended': True,
                'common_attributes': common_attributes
            })
            logger.debug(f"Контентная рекомендация: {dest.recommendation}, score={score * 100}, совпадения={common_attributes}")

    content_recommendations.sort(key=lambda x: x['score'], reverse=True)
    content_recommendations = content_recommendations[:limit * 2]

    # Коллаборативная фильтрация
    all_users = User.objects.all()
    all_destinations = Destination.objects.all()
    user_ids = [u.id for u in all_users]
    dest_ids = [d.id for d in all_destinations]

    interaction_matrix = np.zeros((len(user_ids), len(dest_ids)))
    for inter in UserInteraction.objects.filter(destination__isnull=False):
        user_idx = user_ids.index(inter.user.id)
        dest_idx = dest_ids.index(inter.destination.id)
        if inter.interaction_type == 'view':
            interaction_matrix[user_idx, dest_idx] = 1
        elif inter.interaction_type == 'favorite':
            interaction_matrix[user_idx, dest_idx] = 2
        elif inter.interaction_type == 'review':
            interaction_matrix[user_idx, dest_idx] = 3
        elif inter.interaction_type == 'view_post' and inter.post.destination:
            interaction_matrix[user_idx, dest_idx] = 1.5  # Меньший вес для просмотра поста

    logger.debug(f"Размер матрицы взаимодействий: {interaction_matrix.shape}, ненулевых: {np.count_nonzero(interaction_matrix)}")
    if user.id in user_ids:
        logger.debug(f"Матрица взаимодействий для пользователя {user.id}: {interaction_matrix[user_ids.index(user.id)]}")

    current_user_idx = user_ids.index(user.id) if user.id in user_ids else -1
    if current_user_idx == -1 or np.count_nonzero(interaction_matrix[current_user_idx]) == 0:
        logger.debug("Нет взаимодействий для текущего пользователя, возвращаем контентные рекомендации")
        return content_recommendations[:limit]

    user_vector = interaction_matrix[current_user_idx].reshape(1, -1)
    similarities = cosine_similarity(user_vector, interaction_matrix).flatten()
    similar_user_indices = np.argsort(similarities)[::-1][1:6]

    collab_recommendations = []
    key_tags = {'романтика', 'природа', 'городской отдых', 'релакс'}
    for idx in similar_user_indices:
        if similarities[idx] < 0.1:
            logger.debug(f"Пропущен пользователь {user_ids[idx]} из-за низкой схожести: {similarities[idx]}")
            continue
        similar_user_id = user_ids[idx]
        similar_user_vector = interaction_matrix[idx]
        for dest_idx, score in enumerate(similar_user_vector):
            if score > 0 and dest_ids[dest_idx] not in seen_ids:
                dest = Destination.objects.get(id=dest_ids[dest_idx])
                dest_tags = set(v.lower() for v in dest.tags.values_list('name', flat=True))
                dest_vibes = set(v.lower() for v in dest.vibe.values_list('name', flat=True))
                common_attributes = (dest_tags | dest_vibes) & user_profile
                if len(common_attributes) < 2 and not (common_attributes & key_tags):
                    continue
                rec_score = score * similarities[idx] * 50
                collab_recommendations.append({
                    'destination': dest,
                    'score': rec_score,
                    'score_percentage': rec_score,
                    'is_popular': dest.is_popular,
                    'is_recommended': True,
                    'common_attributes': common_attributes
                })
                seen_ids.add(dest.id)
                logger.debug(f"Коллаборативная рекомендация: {dest.recommendation}, score={rec_score}, совпадения={common_attributes}")

    collab_recommendations.sort(key=lambda x: x['score'], reverse=True)
    collab_recommendations = collab_recommendations[:limit * 2]

    # Комбинирование
    recommendations = []
    seen_dest_ids = set()
    content_weight = 0.6
    collab_weight = 0.4

    for content_rec in content_recommendations:
        for collab_rec in collab_recommendations:
            if content_rec['destination'].id == collab_rec['destination'].id and content_rec['destination'].id not in seen_dest_ids:
                combined_score = content_rec['score'] * content_weight + collab_rec['score'] * collab_weight
                recommendations.append({
                    'destination': content_rec['destination'],
                    'score': combined_score,
                    'score_percentage': combined_score,
                    'is_popular': content_rec['is_popular'],
                    'is_recommended': True
                })
                seen_dest_ids.add(content_rec['destination'].id)
                logger.debug(f"Комбинированная рекомендация: {content_rec['destination'].recommendation}, score={combined_score}")

    for rec in content_recommendations:
        if rec['destination'].id not in seen_dest_ids:
            recommendations.append({
                'destination': rec['destination'],
                'score': rec['score'] * content_weight,
                'score_percentage': rec['score_percentage'] * content_weight,
                'is_popular': rec['is_popular'],
                'is_recommended': True
            })
            seen_dest_ids.add(rec['destination'].id)

    for rec in collab_recommendations:
        if rec['destination'].id not in seen_dest_ids:
            recommendations.append({
                'destination': rec['destination'],
                'score': rec['score'] * collab_weight,
                'score_percentage': rec['score_percentage'] * collab_weight,
                'is_popular': rec['is_popular'],
                'is_recommended': True
            })
            seen_dest_ids.add(rec['destination'].id)

    recommendations.sort(key=lambda x: x['score'], reverse=True)
    if len(recommendations) < limit:
        remaining = limit - len(recommendations)
        popular_recs = get_popular_recommendations(seen_ids, remaining)
        recommendations.extend(popular_recs)
        logger.debug(f"Добавлены популярные места (fallback): {[r['destination'].recommendation for r in popular_recs]}")

    logger.debug(f"Итоговые гибридные рекомендации: {[r['destination'].recommendation for r in recommendations]}")
    return recommendations[:limit]


from collections import Counter
import random
from datetime import timedelta
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from django.utils import timezone
import logging
from .models import InspirationPost, UserInteraction

logger = logging.getLogger(__name__)

def sort_inspiration_posts(user, posts):
    if not posts:
        return []

    # Собираем ID взаимодействованных постов для аутентифицированных пользователей
    seen_post_ids = set()
    if user.is_authenticated:
        interactions = UserInteraction.objects.filter(user=user, post__isnull=False)
        seen_post_ids = set(inter.post.id for inter in interactions if inter.post)
        seen_post_ids.update(InspirationPost.objects.filter(user=user).values_list('id', flat=True))
        logger.debug(f"Взаимодействованные посты: {seen_post_ids}")

    # Определяем популярные посты (по лайкам и сохранениям)
    popular_posts = InspirationPost.objects.order_by('-likes', '-saved_by_users')[:20]
    popular_post_ids = set(p.id for p in popular_posts)
    logger.debug(f"Популярные посты: {popular_post_ids}")

    # Определяем новые посты (за последние 7 дней)
    new_post_threshold = timezone.now() - timedelta(days=7)
    new_post_ids = set(InspirationPost.objects.filter(created_at__gte=new_post_threshold).values_list('id', flat=True))
    logger.debug(f"Новые посты: {new_post_ids}")

    # Создаем профиль пользователя для аутентифицированных пользователей
    user_profile = []
    interaction_weights = {
        'save_post': 3.0,
        'like_post': 2.0,
        'view_post': 0.5,
        'favorite': 2.5,
        'review': 2.0,
        'search': 1.5,
    }

    if user.is_authenticated:
        interactions = UserInteraction.objects.filter(user=user).order_by('-created_at')[:50]
        for inter in interactions:
            weight = interaction_weights.get(inter.interaction_type, 1.0)
            if inter.interaction_type == 'search' and inter.search_filters:
                for key in ['tags', 'vibe']:
                    if inter.search_filters.get(key):
                        if isinstance(inter.search_filters[key], list):
                            user_profile.extend([f"{v.lower().replace(' ', '_')}:{weight}" for v in inter.search_filters[key] if isinstance(v, str)])
                        elif isinstance(inter.search_filters[key], str):
                            user_profile.append(f"{inter.search_filters[key].lower().replace(' ', '_')}:{weight}")
                if inter.search_filters.get('country'):
                    country = inter.search_filters['country']
                    if isinstance(country, list):
                        user_profile.extend([f"{c.lower()}:{weight}" for c in country if isinstance(c, str)])
                    elif isinstance(country, str):
                        user_profile.append(f"{country.lower()}:{weight}")
                if inter.search_filters.get('climate'):
                    climate = inter.search_filters['climate']
                    if isinstance(climate, list):
                        user_profile.extend([f"{c.lower().replace(' ', '_')}:{weight}" for c in climate if isinstance(c, str)])
                    elif isinstance(climate, str):
                        user_profile.append(f"{climate.lower().replace(' ', '_')}:{weight}")
            elif inter.post and inter.post_filters:
                if inter.post_filters.get('tags'):
                    user_profile.extend([f"{v.lower().replace(' ', '_')}:{weight}" for v in inter.post_filters['tags'] if isinstance(v, str)])
                if inter.post_filters.get('vibe'):
                    user_profile.extend([f"{v.lower().replace(' ', '_')}:{weight}" for v in inter.post_filters['vibe'] if isinstance(v, str)])
            elif inter.destination:
                user_profile.extend([f"{v.lower().replace(' ', '_')}:{weight}" for v in inter.destination.tags.values_list('name', flat=True)])
                user_profile.extend([f"{v.lower().replace(' ', '_')}:{weight}" for v in inter.destination.vibe.values_list('name', flat=True)])
                user_profile.append(f"{inter.destination.country.lower()}:{weight}")
                user_profile.append(f"{inter.destination.climate.lower().replace(' ', '_')}:{weight}")

        # Собственные посты
        own_posts = InspirationPost.objects.filter(user=user)
        for post in own_posts:
            user_profile.extend([f"{v.lower().replace(' ', '_')}:3.0" for v in post.tags.values_list('name', flat=True)])
            user_profile.extend([f"{v.lower().replace(' ', '_')}:3.0" for v in post.vibe.values_list('name', flat=True)])
            if post.destination:
                user_profile.append(f"{post.destination.country.lower()}:3.0")
                user_profile.append(f"{post.destination.climate.lower().replace(' ', '_')}:3.0")
            elif post.pending_destination:
                user_profile.append(f"{post.pending_destination.country.lower()}:3.0")
                if post.pending_destination.climate:
                    user_profile.append(f"{post.pending_destination.climate.lower().replace(' ', '_')}:3.0")

        # Объединяем теги, суммируя веса
        tag_weight_sums = {}
        for tag in user_profile:
            tag_name, weight = tag.split(':')
            weight = float(weight)
            tag_weight_sums[tag_name] = tag_weight_sums.get(tag_name, 0) + weight

        # Топ-10 тегов по сумме весов
        tag_counts = Counter({tag: weight for tag, weight in tag_weight_sums.items()})
        top_tags = [tag for tag, _ in tag_counts.most_common(10)]
        weighted_profile = [f"{tag}:{tag_weight_sums[tag]}" for tag in top_tags]
        user_profile_text = ' '.join(weighted_profile)
        logger.debug(f"Профиль пользователя: {user_profile_text}")
    else:
        user_profile_text = ''
        weighted_profile = []
        tag_weight_sums = {}
        logger.debug("Пользователь не аутентифицирован, профиль пуст")

    # Разделяем посты на невиденные и взаимодействованные
    unseen_posts = [post for post in posts if post.id not in seen_post_ids]
    seen_posts = [post for post in posts if post.id in seen_post_ids]
    logger.debug(f"Невиденные посты: {[p.id for p in unseen_posts]}, Взаимодействованные посты: {[p.id for p in seen_posts]}")

    # Векторизация постов
    post_texts = []
    post_scores = []
    post_tags_list = []

    for post in posts:
        weight = 1.0
        # Бонус за новизну
        if post.created_at >= new_post_threshold:
            weight += random.uniform(0.2, 0.4)
        # Бонус за популярность
        if post.id in popular_post_ids:
            weight += random.uniform(0.3, 0.5)
        # Штраф за взаимодействие (только для аутентифицированных)
        if user.is_authenticated and post.id in seen_post_ids:
            weight *= 0.5
        # Бонус за случайность для разнообразия
        weight += random.uniform(0.1, 0.3)

        text_parts = []
        text_parts.extend([v.lower().replace(' ', '_') for v in post.tags.values_list('name', flat=True)])
        text_parts.extend([v.lower().replace(' ', '_') for v in post.vibe.values_list('name', flat=True)])
        if post.destination:
            text_parts.append(post.destination.country.lower())
            text_parts.append(post.destination.climate.lower().replace(' ', '_'))
            text_parts.extend([v.lower().replace(' ', '_') for v in post.destination.tags.values_list('name', flat=True)])
            text_parts.extend([v.lower().replace(' ', '_') for v in post.destination.vibe.values_list('name', flat=True)])
        elif post.pending_destination:
            text_parts.append(post.pending_destination.country.lower())
            if post.pending_destination.climate:
                text_parts.append(post.pending_destination.climate.lower().replace(' ', '_'))
            try:
                if hasattr(post.pending_destination, 'tags') and post.pending_destination.tags.exists():
                    text_parts.extend([v.lower().replace(' ', '_') for v in post.pending_destination.tags.values_list('name', flat=True)])
                if hasattr(post.pending_destination, 'vibe') and post.pending_destination.vibe.exists():
                    text_parts.extend([v.lower().replace(' ', '_') for v in post.pending_destination.vibe.values_list('name', flat=True)])
            except AttributeError:
                logger.debug(f"У PendingDestination поста {post.id} нет tags или vibe")

        post_text = ' '.join(set(text_parts))
        post_texts.append(post_text)
        post_scores.append({'post': post, 'weight': weight})
        post_tags_list.append(set(text_parts))
        logger.debug(f"Текст поста {post.id}: {post_text}")

    # TF-IDF и косинусное сходство для аутентифицированных пользователей
    if user.is_authenticated and user_profile_text and post_texts:
        vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b\w+\b')
        user_profile_clean = ' '.join(tag.split(':')[0] for tag in weighted_profile)
        post_vectors = vectorizer.fit_transform(post_texts)
        user_vector = vectorizer.transform([user_profile_clean])
        similarity_scores = cosine_similarity(user_vector, post_vectors).flatten()

        feature_names = vectorizer.get_feature_names_out()

        for idx, post_score in enumerate(post_scores):
            post = post_score['post']
            score = similarity_scores[idx]
            post_tags = post_tags_list[idx]
            user_tags = set(tag.split(':')[0] for tag in weighted_profile)
            matching_tags = post_tags.intersection(user_tags)
            tag_contributions = []
            if matching_tags:
                post_vector = post_vectors[idx].toarray()[0]
                user_vector_array = user_vector.toarray()[0]
                for tag in matching_tags:
                    if tag in feature_names:
                        tag_idx = np.where(feature_names == tag)[0]
                        if tag_idx.size > 0:
                            tfidf_score = post_vector[tag_idx[0]] * user_vector_array[tag_idx[0]]
                            max_weight = max(list(tag_weight_sums.values()) + [1.0])
                            tag_weight = tag_weight_sums.get(tag, 1.0) / max_weight
                            adjusted_score = tfidf_score * tag_weight
                            tag_contributions.append(f"{tag} (вклад: {adjusted_score:.4f})")
                contributions_str = ", ".join(tag_contributions) if tag_contributions else "нет совпадений"
                final_score = score * post_score['weight'] * (1 + sum(tag_weight_sums.get(tag, 0) for tag in matching_tags) / max(list(tag_weight_sums.values()) + [1.0]))
                logger.debug(f"Пост {post.id}: score={score:.4f}, weight={post_score['weight']:.4f}, final_score={final_score:.4f}, совпадения: {contributions_str}")
            else:
                final_score = score * post_score['weight']
                logger.debug(f"Пост {post.id}: score={score:.4f}, weight={post_score['weight']:.4f}, final_score={final_score:.4f}, совпадений нет")
            post_score['score'] = final_score
    else:
        # Для неаутентифицированных пользователей или пустого профиля
        for post_score in post_scores:
            post = post_score['post']
            final_score = post_score['weight']
            logger.debug(f"Пост {post.id}: score={final_score:.4f}, weight={post_score['weight']:.4f}, final_score={final_score:.4f}, профиль пуст или пользователь не аутентифицирован")
            post_score['score'] = final_score

    # Сортировка постов
    sorted_posts = sorted(post_scores, key=lambda x: x['score'], reverse=True)
    return [item['post'] for item in sorted_posts]
