import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_protect

from .forms import SearchForm, LoginForm, RegisterForm, ReviewForm
from .models import Destination, Review, UserProfile, Result, UserInteraction
from .utils import handle_review_form, calculate_ratings
from .rec import get_filtered_destinations, get_user_behavior_recommendations


import requests
import re
import json
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def get_recommendations(user, exclude_destination_ids, limit=4):
    recommendations = []

    if user.is_authenticated:
        # Собираем все взаимодействия пользователя
        interactions = UserInteraction.objects.filter(user=user).order_by('-created_at')
        if not interactions.exists():
            logger.debug(f"Для пользователя {user.username} нет взаимодействий в базе travel_app_userinteraction")

        # Собираем ID всех мест, с которыми пользователь взаимодействовал
        seen_ids = set(inter.destination.id for inter in interactions if inter.destination)
        seen_ids.update(exclude_destination_ids)

        # 1. Приоритет: последний поиск
        search_inter = interactions.filter(interaction_type='search').first()
        if search_inter and search_inter.search_filters:
            logger.debug(f"Найден последний поиск для {user.username}: {search_inter.search_filters}")
            recs = get_user_behavior_recommendations(user, search_inter.search_filters, seen_ids, limit)
            for rec in recs:
                recommendations.append(rec)
                logger.debug(
                    f"Добавлено по последнему поиску: {rec['destination'].recommendation}, "
                    f"score={rec['score']}, "
                    f"причина: похож на фильтры поиска {search_inter.search_filters}"
                )

        # 2. Если нет поиска: избранное
        if len(recommendations) < limit:
            favorite_inter = interactions.filter(interaction_type='favorite')
            for inter in favorite_inter[:2]:  # Ограничиваем 2 избранными для разнообразия
                if inter.destination:
                    # Формируем фильтры на основе избранного места
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
                    for rec in recs:
                        recommendations.append(rec)
                        logger.debug(
                            f"Добавлено по избранному: {rec['destination'].recommendation}, "
                            f"score={rec['score']}, "
                            f"причина: похож на избранное {inter.destination.recommendation}"
                        )

        # 3. Если недостаточно: просмотры
        if len(recommendations) < limit:
            view_inter = interactions.filter(interaction_type='view')
            for inter in view_inter[:2]:  # Ограничиваем 2 просмотрами
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
                    for rec in recs:
                        recommendations.append(rec)
                        logger.debug(
                            f"Добавлено по просмотрам: {rec['destination'].recommendation}, "
                            f"score={rec['score']}, "
                            f"причина: похож на просмотренное {inter.destination.recommendation}"
                        )

        # 4. Если недостаточно: отзывы
        if len(recommendations) < limit:
            review_inter = interactions.filter(interaction_type='review')
            for inter in review_inter[:2]:  # Ограничиваем 2 отзывами
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
                    for rec in recs:
                        recommendations.append(rec)
                        logger.debug(
                            f"Добавлено по отзывам: {rec['destination'].recommendation}, "
                            f"score={rec['score']}, "
                            f"причина: похож на место с отзывом {inter.destination.recommendation}"
                        )

    # 5. Fallback: популярные места
    if len(recommendations) < limit:
        seen_ids = set(
            inter.destination.id for inter in interactions if inter.destination) if user.is_authenticated else set()
        seen_ids.update(exclude_destination_ids)
        popular_recs = get_user_behavior_recommendations(user, {}, seen_ids, limit - len(recommendations))
        for rec in popular_recs:
            recommendations.append(rec)
            logger.debug(
                f"Добавлено по популярности: {rec['destination'].recommendation}, "
                f"score={rec['score']}, "
                f"причина: популярное место, не взаимодействовал"
            )

    # Сортировка и ограничение
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    recommendations = recommendations[:limit]

    if not recommendations:
        logger.debug(f"Для пользователя {user.username} не удалось сформировать рекомендации")

    return recommendations

def home(request):
    recommendations = {
        'by_interactions': []
    }
    if request.user.is_authenticated:
        recommendations = get_recommendations(request.user, [])
    return render(request, 'travel_app/index.html', {
        'recommendations': recommendations
    })


def show_all(request):
    all_destinations = Destination.objects.all()
    return render(request, 'travel_app/index.html', {'all_destinations': all_destinations})


def chatbot(request):
    if request.method == 'POST':
        message = request.POST.get('message', '').lower()
        logger.debug(f"Получен запрос: {message}")
        # Запрос к YandexGPT
        api_key = settings.YANDEX_API_KEY
        catalog_id = settings.YANDEX_CATALOG_ID
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {
            "Authorization": f"Api-Key {api_key}",
            "Content-Type": "application/json"
        }
        prompt = (
            f"Извлеки фильтры для поиска места отдыха из текста: '{message}'. "
            "Верни JSON с полями: country, activity_type, comfort_level, tags. "
            "Если поле не указано, оставь пустым. Например: "
            '{"country": "Турция", "activity_type": "Пляжный", "comfort_level": "", "tags": "романтика"}'
        )
        payload = {
            "modelUri": f"gpt://{catalog_id}/yandexgpt-lite",
            "completionOptions": {
                "stream": False,
                "temperature": 0.6,
                "maxTokens": 200
            },
            "messages": [
                {"role": "user", "text": prompt}
            ]
        }
        logger.debug(f"Отправка запроса к {url} с payload: {payload}")
        response = requests.post(url, headers=headers, json=payload)
        logger.debug(f"Ответ от API: {response.status_code} - {response.text}")
        if response.status_code != 200:
            return JsonResponse({'reply': 'Ошибка связи с ИИ. Проверьте лог.'})

        # Извлечение текста ответа
        raw_response = response.json().get('result', {}).get('alternatives', [{}])[0].get('message', {}).get('text',
                                                                                                             '{}')

        # Удаление Markdown и переносов строк
        clean_response = re.sub(r'```(?:json)?\n|\n```', '', raw_response).strip()
        logger.debug(f"Очищенный ответ: {clean_response}")

        # Парсинг JSON
        try:
            # Если ответ — список, берём первый элемент
            if clean_response.startswith('['):
                filters_list = json.loads(clean_response)
                filters = filters_list[0] if filters_list else {}
            else:
                filters = json.loads(clean_response)
            logger.debug(f"Извлечённые фильтры: {filters}")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON: {e}")
            return JsonResponse({'reply': 'Ошибка обработки ответа ИИ.'})

        # Поиск в базе
        destinations = Destination.objects.filter(
            country__icontains=filters.get('country', ''),
            activity_type__icontains=filters.get('activity_type', ''),
            comfort_level__icontains=filters.get('comfort_level', ''),
            tags__icontains=filters.get('tags', '')
        )[:3]
        if destinations.exists():
            reply = "Вот что я нашёл:\n" + "\n".join([d.recommendation for d in destinations])
        else:
            reply = "К сожалению, ничего не найдено."
        return JsonResponse({'reply': reply})
    return JsonResponse({'reply': 'Опишите, куда хотите поехать!'})


def search(request):
    form = SearchForm(request.GET or None)
    destinations, message, page_obj = get_filtered_destinations(request, form)
    exclude_ids = [d['destination'].id for d in destinations]
    recommended_destinations = get_user_behavior_recommendations(
        request.user,
        form.cleaned_data if form.is_valid() else {},
        exclude_ids
    )

    print("Форма валидна:", form.is_valid())
    print("Данные в форме:", form.data)
    print("Season (getlist):", request.GET.getlist('season'))
    if form.is_valid():
        print("Season (form.cleaned_data):", form.cleaned_data.get('season'))
    else:
        print("Форма невалидна. Ошибки:", form.errors)

    return render(request, 'travel_app/search.html', {
        'form': form,
        'destinations': page_obj,
        'message': message,
        'recommended_destinations': recommended_destinations,
        'page_obj': page_obj,
    })


def destination_detail(request, pk):
    destination = get_object_or_404(Destination, pk=pk)
    if request.user.is_authenticated:
        UserInteraction.objects.create(
            user=request.user,
            destination=destination,
            interaction_type='view'
        )
    reviews = Review.objects.filter(destination=destination)
    user_review = None
    is_favorite = False

    if request.user.is_authenticated:
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        user_review = Review.objects.filter(destination=destination, user=request.user).first()
        is_favorite = user_profile.results.filter(recommendation=destination.recommendation).exists()

    average_rating, average_stars, reviews_with_stars = calculate_ratings(reviews)

    if request.method == 'POST':
        success, error = handle_review_form(request, destination, user_review)
        if success:
            return redirect('destination_detail', pk=pk)
        messages.error(request, error)

    form = ReviewForm()
    return render(request, 'travel_app/destination_detail.html', {
        'destination': destination,
        'reviews_with_stars': reviews_with_stars,
        'form': form,
        'user_review': user_review,
        'average_rating': average_rating,
        'average_stars': average_stars,
        'is_favorite': is_favorite,
    })


# Представления для авторизации
@csrf_protect
def loginPage(request):
    form = LoginForm()
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(request, username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            if user is not None:
                login(request, user)
                return redirect('index')
            else:
                form.add_error(None, 'Неверные данные!')
    return render(request, 'travel_app/login.html', {'form': form})


def registerPage(request):
    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            return redirect('login')
    return render(request, 'travel_app/registration.html', {'form': form})


def doLogout(request):
    logout(request)
    return redirect('login')


# Представления для профиля
@login_required
def profile(request):
    if request.user.is_authenticated:
        user_reviews = Review.objects.filter(user=request.user)
        return render(request, 'travel_app/profile.html', {
            'user': request.user,
            'user_reviews': user_reviews,
        })
    return redirect('login')


@login_required
def add_to_profile(request, recommendation):
    user = request.user
    user_profile, created = UserProfile.objects.get_or_create(user=user)
    if not user_profile.results.filter(recommendation=recommendation).exists():
        result = Result.objects.create(user=user, recommendation=recommendation)
        user_profile.results.add(result)
    return redirect('profile')


def delete_result(request, result_id):
    if request.user.is_authenticated:
        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.delete_result(result_id)
    return redirect('profile')


# Представления для отзывов и избранного
@login_required
def add_review(request, pk):
    destination = get_object_or_404(Destination, pk=pk)
    user_review = Review.objects.filter(destination=destination, user=request.user).first()

    if request.method == 'POST':
        success, error = handle_review_form(request, destination, user_review)
        if success:
            UserInteraction.objects.create(
                user=request.user,
                destination=destination,
                interaction_type='review'
            )
            return redirect('destination_detail', pk=pk)
        messages.error(request, error)

    form = ReviewForm()
    return render(request, 'travel_app/review.html', {'form': form, 'destination': destination})


@login_required
def delete_review(request, pk):
    review = get_object_or_404(Review, pk=pk)
    if request.method == 'POST':
        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.delete_review(review.id)
        review.delete()
        next_url = request.POST.get('next', 'profile')
        return redirect(next_url)
    return redirect('profile')


@login_required
def toggle_favorite(request, pk):
    destination = get_object_or_404(Destination, pk=pk)
    user_profile = UserProfile.objects.get(user=request.user)
    favorite = user_profile.results.filter(recommendation=destination.recommendation).first()
    if favorite:
        user_profile.results.remove(favorite)
        favorite.delete()
    else:
        user_profile.add_result(destination)
        UserInteraction.objects.create(
            user=request.user,
            destination=destination,
            interaction_type='favorite'
        )
    return redirect('destination_detail', pk=pk)


def add_result_to_profile(user, recommendation):
    result = Result(user=user, recommendation=recommendation)
    result.save()
