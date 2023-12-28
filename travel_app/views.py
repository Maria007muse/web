from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import *

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
    # инициализируем объект формы
    form = RegisterForm()

    if request.method == 'POST':
        # заполняем объект данными формы, если она была отправлена
        form = RegisterForm(request.POST)

        if form.is_valid():
            # если форма валидна - создаем нового пользователя
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            return redirect('login')
    # ренедерим шаблон и передаем объект формы
    return render(request, 'travel_app/registration.html', {'form': form})

def profile(request):
    if request.user.is_authenticated:
        return render(request, 'travel_app/profile.html', {'user': request.user})
    else:
       return redirect('login')


from django.shortcuts import render, redirect
from django.contrib.auth import logout
from .forms import SearchForm
from .models import Result, UserProfile, Destination

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

# выход
def doLogout(request):
    # вызываем функцию django.contrib.auth.logout и делаем редирект на страницу входа
    logout(request)
    return redirect('login')







