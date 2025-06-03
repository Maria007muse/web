from django.db.models import Q, Avg
from django.core.paginator import Paginator
from .models import Destination, UserInteraction
import logging

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
    if filters.get('activity_type'):
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
        'activity_types': 15,  # Исправлено: 'activity_type' на 'activity_types'
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

        # Исключаем взаимодействованные места
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
        exclude_ids = set(exclude_destination_ids) | {r['destination'].id for r in recommendations}  # Объединяем в множество
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
        exclude_ids = set(exclude_destination_ids) | {r['destination'].id for r in recommendations}  # Объединяем в множество
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
