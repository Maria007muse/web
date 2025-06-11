import logging
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.forms import formset_factory
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.conf import settings
import requests
import re
import json
from .forms import SearchForm, LoginForm, RegisterForm, ReviewForm, InspirationPostForm, RoutePointForm, RouteForm
from .models import Destination, Review, UserProfile, Result, UserInteraction, InspirationPost, PendingDestination, \
    Vibe, Tag, Route, RoutePoint
from .utils import handle_review_form, calculate_ratings
from .rec import get_filtered_destinations, get_personalized_recommendations, get_seasonal_recommendations, \
    get_seasonal_personal_recommendations, get_inspiration_recommendations, get_trending_recommendations, \
    get_similar_users_recommendations, sort_inspiration_posts

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def home(request):
    seasonal_destinations = get_seasonal_recommendations()
    personalized_seasonal = get_seasonal_personal_recommendations(request.user) if request.user.is_authenticated else []
    recommendations = get_personalized_recommendations(request.user, []) if request.user.is_authenticated else []
    inspiration_recommendations = get_inspiration_recommendations(request.user) if request.user.is_authenticated else []
    trending_recommendations = get_trending_recommendations()
    similar_users_recommendations = get_similar_users_recommendations(request.user, []) if request.user.is_authenticated else []

    return render(request, 'travel_app/index.html', {
        'recommendations': recommendations,
        'seasonal_destinations': seasonal_destinations,
        'personalized_seasonal': personalized_seasonal,
        'inspiration_recommendations': inspiration_recommendations,
        'trending_recommendations': trending_recommendations,
        'similar_users_recommendations': similar_users_recommendations,
    })


def show_all(request):
    all_destinations = Destination.objects.all()
    return render(request, 'travel_app/index.html', {'all_destinations': all_destinations})

def chatbot(request):
    if request.method == 'POST':
        message = request.POST.get('message', '').lower()
        logger.debug(f"Получен запрос: {message}")
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

        raw_response = response.json().get('result', {}).get('alternatives', [{}])[0].get('message', {}).get('text', '{}')
        clean_response = re.sub(r'```(?:json)?\n|\n```', '', raw_response).strip()
        logger.debug(f"Очищенный ответ: {clean_response}")

        try:
            if clean_response.startswith('['):
                filters_list = json.loads(clean_response)
                filters = filters_list[0] if filters_list else {}
            else:
                filters = json.loads(clean_response)
            logger.debug(f"Извлечённые фильтры: {filters}")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON: {e}")
            return JsonResponse({'reply': 'Ошибка обработки ответа ИИ.'})

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
    recommended_destinations = get_personalized_recommendations(
        request.user,
        exclude_ids,
        limit=4
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

@login_required
def profile(request):
    if request.user.is_authenticated:
        user_reviews = Review.objects.filter(user=request.user)
        user_posts = InspirationPost.objects.filter(user=request.user).order_by('-created_at')
        saved_posts = UserProfile.objects.get(user=request.user).saved_inspiration_posts.all().order_by('-created_at')
        liked_posts = InspirationPost.objects.filter(likes=request.user).order_by('-created_at')
        return render(request, 'travel_app/profile.html', {
            'user': request.user,
            'user_reviews': user_reviews,
            'user_posts': user_posts,
            'saved_posts': saved_posts,
            'liked_posts': liked_posts,
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

@login_required
def create_inspiration_post(request):
    if request.method == 'POST':
        form = InspirationPostForm(request.POST, request.FILES)
        print("Form data:", request.POST, request.FILES)  # Отладка: данные формы
        print("Form errors:", form.errors)  # Отладка: ошибки формы
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            if form.cleaned_data.get('pending_destination_name'):
                pending_destination = PendingDestination.objects.create(
                    name=form.cleaned_data['pending_destination_name'],
                    country=form.cleaned_data['pending_destination_country'],
                    city=form.cleaned_data['pending_destination_city'],
                    description=form.cleaned_data['description'],
                    user=request.user,
                    image=form.cleaned_data['image'],
                    climate=form.cleaned_data.get('climate'),  # Если климат есть в форме
                    season=form.cleaned_data.get('season'),  # Если сезон есть в форме
                )
                # Сохраняем теги и атмосферу
                tags = Tag.objects.filter(name__in=form.cleaned_data['tags'])
                vibe = Vibe.objects.filter(name__in=form.cleaned_data['vibe'])
                print("Selected tags:", tags)  # Отладка: выбранные теги
                print("Selected vibe:", vibe)  # Отладка: выбранная атмосфера
                pending_destination.tags.set(tags)
                pending_destination.vibe.set(vibe)
                post.pending_destination = pending_destination
            post.save()
            try:
                user_profile, created = UserProfile.objects.get_or_create(user=request.user)
                user_profile.add_post(post)
                messages.success(request, 'Ваш пост успешно добавлен! Новое место ожидает модерации.')
                return redirect('inspiration_feed')
            except AttributeError as e:
                logger.error(f"Ошибка при добавлении поста в профиль: {e}")
                messages.error(request, 'Ошибка при сохранении поста. Обратитесь к администратору.')
        else:
            messages.error(request, f'Ошибка при создании поста: {form.errors}')
    else:
        form = InspirationPostForm()
    return render(request, 'travel_app/create_inspiration_post.html', {'form': form})


@login_required
def toggle_like_post(request, pk):
    post = get_object_or_404(InspirationPost, pk=pk)
    user_profile = UserProfile.objects.get(user=request.user)

    if request.user in post.likes.all():
        post.likes.remove(request.user)
        UserInteraction.objects.filter(user=request.user, post=post, interaction_type='like_post').delete()
        messages.success(request, 'Лайк удален.')
    else:
        post.likes.add(request.user)
        post_filters = {
            'tags': list(post.tags.values_list('name', flat=True)),
            'vibe': list(post.vibe.values_list('name', flat=True))
        }
        UserInteraction.objects.create(
            user=request.user,
            post=post,
            destination=post.destination,
            interaction_type='like_post',
            post_filters=post_filters if post_filters['tags'] or post_filters['vibe'] else None
        )
        messages.success(request, 'Лайк добавлен.')

    return redirect(request.POST.get('next', 'inspiration_feed'))


def inspiration_feed(request):
    logger.debug(f"Пользователь: {request.user}, аутентифицирован: {request.user.is_authenticated}")

    # Получаем посты
    if request.user.is_authenticated:
        posts = InspirationPost.objects.exclude(user=request.user).order_by('-created_at')
    else:
        posts = InspirationPost.objects.all().order_by('-created_at')
    logger.debug(f"Запрошено постов: {posts.count()}")

    # Обработка клика по карточке (POST-запрос)
    if request.method == 'POST':
        post_id = request.POST.get('post_id')
        if post_id:
            try:
                post = InspirationPost.objects.get(id=post_id)
                # Записываем взаимодействие только для аутентифицированных пользователей
                if request.user.is_authenticated:
                    UserInteraction.objects.create(
                        user=request.user,
                        interaction_type='view_post',
                        post=post
                    )
                    logger.debug(f"Взаимодействие записано: пользователь {request.user}, пост {post.id}")

                # Формируем данные для модального окна
                data = {
                    'name': post.destination.recommendation if post.destination else post.pending_destination.name,
                    'description': post.description or '',
                    'image_url': post.image.url if post.image else '/static/placeholder.jpg',
                    'tags': [tag.name for tag in post.tags.all()],
                    'vibe': [vibe.name for vibe in post.vibe.all()],
                    'created_at': post.created_at.strftime('%d.%m.%Y'),
                    'author': post.user.username,
                    'likes_count': post.likes.count(),
                    'destination_id': post.destination.id if post.destination else None,
                }
                return JsonResponse(data)
            except InspirationPost.DoesNotExist:
                logger.error(f"Пост с id {post_id} не найден")
                return JsonResponse({'error': 'Post not found'}, status=404)
        return JsonResponse({'error': 'No post_id provided'}, status=400)

    # Сортируем посты с помощью функции рекомендаций
    sorted_posts = sort_inspiration_posts(request.user, posts)

    context = {
        'posts': sorted_posts,
    }
    return render(request, 'travel_app/inspiration_feed.html', context)


@login_required
def save_inspiration_post(request, pk):
    post = get_object_or_404(InspirationPost, pk=pk)
    if request.user == post.user:
        messages.error(request, 'Нельзя сохранять свои посты.')
        return redirect('inspiration_feed')
    user_profile = UserProfile.objects.get(user=request.user)
    if post not in user_profile.saved_inspiration_posts.all():
        user_profile.add_saved_post(post)
        post_filters = {
            'tags': list(post.tags.values_list('name', flat=True)),
            'vibe': list(post.vibe.values_list('name', flat=True))
        }
        UserInteraction.objects.create(
            user=request.user,
            post=post,
            destination=post.destination,
            interaction_type='save_post',
            post_filters=post_filters if post_filters['tags'] or post_filters['vibe'] else None
        )
        messages.success(request, 'Пост сохранен в Вдохновение.')
    else:
        messages.info(request, 'Пост уже сохранен.')
    return redirect('inspiration_feed')

@login_required
def remove_saved_post(request, pk):
    post = get_object_or_404(InspirationPost, pk=pk)
    if request.method == 'POST':
        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.remove_saved_post(post.id)
        messages.success(request, 'Пост удален из Вдохновения.')
        next_url = request.POST.get('next', 'profile')
        return redirect(next_url)
    return redirect('profile')


@login_required
def delete_post(request, pk):
    post = get_object_or_404(InspirationPost, pk=pk, user=request.user)
    if request.method == 'POST':
        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.delete_post(post.id)
        post.delete()
        messages.success(request, 'Пост успешно удален.')
        next_url = request.POST.get('next', 'profile')
        return redirect(next_url)
    return redirect('profile')


RoutePointFormSet = formset_factory(RoutePointForm, extra=1)


# travel_app/views.py
@login_required
def create_route(request):
    if request.method == 'POST':
        route_form = RouteForm(request.POST, request.FILES)
        point_formset = RoutePointFormSet(request.POST, request.FILES, prefix='points')
        if route_form.is_valid() and point_formset.is_valid():
            route = route_form.save(commit=False)
            route.user = request.user
            route.save()

            valid_points = 0
            for index, form in enumerate(point_formset):
                cleaned_data = form.cleaned_data
                # Пропускаем пустые формы
                if cleaned_data and (
                        cleaned_data.get('destination') or cleaned_data.get('custom_name') or cleaned_data.get(
                        'note') or cleaned_data.get('image')):
                    point = form.save(commit=False)
                    point.route = route
                    point.order = index + 1
                    point.save()
                    valid_points += 1

            if valid_points == 0:
                route.delete()
                messages.error(request, 'Добавьте хотя бы одну точку с местом или названием.')
                return redirect('create_route')

            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            user_profile.add_route(route)
            messages.success(request, 'Маршрут успешно создан!')
            return redirect('route_detail', route_id=route.id)
        else:
            messages.error(request, f'Ошибка: {route_form.errors} {point_formset.errors}')
    else:
        route_form = RouteForm()
        point_formset = RoutePointFormSet(prefix='points')

    return render(request, 'travel_app/create_route.html', {
        'route_form': route_form,
        'point_formset': point_formset,
        'title': 'Создать маршрут',
        'submit_button': 'Сохранить маршрут',
    })


# views.py
@login_required
def create_route(request):
    if request.method == 'POST':
        route_form = RouteForm(request.POST)
        point_formset = RoutePointFormSet(request.POST, prefix='points')
        if route_form.is_valid() and point_formset.is_valid():
            route = route_form.save(commit=False)
            route.user = request.user
            route.save()

            valid_points = 0
            for index, form in enumerate(point_formset):
                cleaned_data = form.cleaned_data
                if cleaned_data and (cleaned_data.get('destination') or cleaned_data.get('custom_name')):
                    point = form.save(commit=False)
                    point.route = route
                    point.order = index + 1
                    point.save()
                    valid_points += 1
                else:
                    logger.debug(f"Пропущена точка {index + 1}: {cleaned_data}")

            if valid_points == 0:
                route.delete()
                messages.error(request, 'Добавьте хотя бы одну точку с местом или названием.')
                return redirect('create_route')

            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            user_profile.add_route(route)
            messages.success(request, 'Маршрут успешно создан!')
            return redirect('route_detail', route_id=route.id)
        else:
            logger.error(f'Ошибки формы: {route_form.errors} {point_formset.errors}')
            messages.error(request, f'Ошибка: {route_form.errors} {point_formset.errors}')
    else:
        route_form = RouteForm()
        point_formset = RoutePointFormSet(prefix='points')

    return render(request, 'travel_app/create_route.html', {
        'route_form': route_form,
        'point_formset': point_formset,
        'title': 'Создать маршрут',
        'submit_button': 'Сохранить маршрут',
    })

@login_required
def edit_route(request, route_id):
    route = get_object_or_404(Route, id=route_id, user=request.user)
    RoutePointFormSet = formset_factory(RoutePointForm, extra=0)
    if request.method == 'POST':
        route_form = RouteForm(request.POST, instance=route)
        point_formset = RoutePointFormSet(request.POST, prefix='points')
        if route_form.is_valid() and point_formset.is_valid():
            route_form.save()

            route.points.all().delete()
            valid_points = 0
            for index, form in enumerate(point_formset):
                cleaned_data = form.cleaned_data
                if cleaned_data and (cleaned_data.get('destination') or cleaned_data.get('custom_name')):
                    point = form.save(commit=False)
                    point.route = route
                    point.order = index + 1
                    point.save()
                    valid_points += 1
                else:
                    logger.debug(f"Пропущена точка {index + 1}: {cleaned_data}")

            if valid_points == 0:
                messages.error(request, 'Добавьте хотя бы одну точку с местом или названием.')
                return redirect('edit_route', route_id=route.id)

            messages.success(request, 'Маршрут обновлён!')
            return redirect('route_detail', route_id=route.id)
        else:
            logger.error(f'Ошибки формы: {route_form.errors} {point_formset.errors}')
            messages.error(request, f'Ошибка: {route_form.errors} {point_formset.errors}')
    else:
        route_form = RouteForm(instance=route)
        point_formset = RoutePointFormSet(
            initial=[{
                'destination': point.destination,
                'custom_name': point.custom_name,
                'note': point.note,
                'date_time': point.date_time,
                'id': point.id,
            } for point in route.points.all()],
            prefix='points'
        )

    return render(request, 'travel_app/edit_route_point.html', {
        'route_form': route_form,
        'point_formset': point_formset,
        'title': 'Редактировать маршрут',
        'submit_button': 'Сохранить изменения',
        'cancel_url': 'route_detail',
        'cancel_url_id': route.id,
    })

@login_required
def route_detail(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    points = route.points.all()
    return render(request, 'travel_app/route_detail.html', {
        'route': route,
        'points': points,
    })


@login_required
def delete_route(request, route_id):
    route = get_object_or_404(Route, id=route_id, user=request.user)
    if request.method == 'POST':
        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.remove_route(route.id)
        route.delete()
        messages.success(request, 'Маршрут удалён!')
        return redirect('profile')
    return redirect('route_detail', route_id=route_id)


@login_required
def delete_route_point(request, point_id):
    point = get_object_or_404(RoutePoint, id=point_id, route__user=request.user)
    route_id = point.route.id
    if request.method == 'POST':
        point.delete()
        for index, p in enumerate(point.route.points.all(), start=1):
            p.order = index
            p.save()
        messages.success(request, 'Точка удалена!')
    return redirect('route_detail', route_id=route_id)


@login_required
def reorder_route_points(request, route_id):
    route = get_object_or_404(Route, id=route_id, user=request.user)
    if request.method == 'POST':
        try:
            order = json.loads(request.POST.get('order', '[]'))
            for index, point_id in enumerate(order, start=1):
                point = RoutePoint.objects.get(id=point_id, route=route)
                point.order = index
                point.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
