from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import *

from .forms import *
from .models import *


def home(request):
    return render(request, 'travel_app/index.html')


def show_all(request):
    all_destinations = Destination.objects.all()
    return render(request, 'travel_app/index.html', {'all_destinations': all_destinations})


def search(request):
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            climate = form.cleaned_data['climate']
            activity_type = form.cleaned_data['activity_type']
            budget = form.cleaned_data['budget']
            popularity = form.cleaned_data['popularity']
            cultural_diversity = form.cleaned_data['cultural_diversity']

            destinations = get_destinations(climate, activity_type, budget, popularity, cultural_diversity)

            return render(request, 'travel_app/leisure.html', {'form': form, 'destinations': destinations})
    else:
        form = SearchForm()

    return render(request, 'travel_app/leisure.html', {'form': form, 'destinations': None})


def get_destinations(climate, activity_type, budget, popularity, cultural_diversity):
    try:
        destinations = Destination.objects.filter(
            climate=climate,
            activity_type=activity_type,
            budget=budget,
            popularity=popularity,
            cultural_diversity=cultural_diversity
        )
    except Destination.DoesNotExist:
        destinations = None

    return destinations


def add_result_to_profile(user, recommendation):
    result = Result(user=user, recommendation=recommendation)
    result.save()


from django.views.decorators.csrf import csrf_protect


@csrf_protect
def loginPage(request):
    # инициализируем объект класса формы
    form = LoginForm()

    # обрабатываем случай отправки формы на этот адрес
    if request.method == 'POST':

        # заполянем объект данными, полученными из запроса
        form = LoginForm(request.POST)

        # проверяем валидность формы
        if form.is_valid():
            # пытаемся авторизовать пользователя
            user = authenticate(request, username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            if user is not None:
                # если существует пользователь с таким именем и паролем,
                # то сохраняем авторизацию и делаем редирект
                login(request, user)
                return redirect('index')
            else:
                # иначе возвращаем ошибку
                form.add_error(None, 'Неверные данные!')

    # рендерим шаблон и передаем туда объект формы
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


@login_required
def profile(request):
    if request.user.is_authenticated:
        user_reviews = Review.objects.filter(user=request.user)
        return render(request, 'travel_app/profile.html', {
            'user': request.user,
            'user_reviews': user_reviews,
        })
    else:
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


def destination_detail(request, pk):
    destination = get_object_or_404(Destination, pk=pk)
    reviews = Review.objects.filter(destination=destination)
    user_review = None
    is_favorite = False

    if request.user.is_authenticated:
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        user_review = Review.objects.filter(destination=destination, user=request.user).first()
        is_favorite = user_profile.results.filter(recommendation=destination.recommendation).exists()
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    rounded_average_rating = round(average_rating)
    average_stars = [True if i <= rounded_average_rating else False for i in range(1, 6)]

    reviews_with_stars = []
    for review in reviews:
        stars = [True if i <= review.rating else False for i in range(1, 6)]
        reviews_with_stars.append((review, stars))

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            if user_review is None:
                review = form.save(commit=False)
                review.user = request.user
                review.destination = destination
                review.save()
                if request.user.is_authenticated:
                    user_profile.add_review(review)
                return redirect('destination_detail', pk=pk)
            else:
                messages.error(request, 'Отзыв уже добавлен.')
    else:
        form = ReviewForm()

    return render(request, 'travel_app/artical_leisure.html', {
        'destination': destination,
        'reviews_with_stars': reviews_with_stars,
        'form': form,
        'user_review': user_review,
        'average_rating': average_rating,
        'average_stars': average_stars,
        'is_favorite': is_favorite,
    })



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

    return redirect('destination_detail', pk=pk)


def doLogout(request):
    logout(request)
    return redirect('login')


@login_required
def add_review(request, pk):
    destination = get_object_or_404(Destination, pk=pk)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.destination = destination

            if len(review.text.strip()) >= 50:
                review.save()
                user_profile, created = UserProfile.objects.get_or_create(user=request.user)
                user_profile.add_review(review)
                return redirect('destination_detail', pk=pk)
            else:
                messages.error(request, 'Комментарий должен содержать не менее 50 символов.')
        else:
            messages.error(request, 'Пожалуйста, выберите рейтинг от 1 до 5.')
    else:
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
