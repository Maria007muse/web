from django.urls import path
from .views import *


urlpatterns = [
    path('', home, name='index'),
    path('leisure/', search, name='leisure'),
    path('login', loginPage, name='login'),
    path('register', registerPage, name='register'),
    path('profile/', profile, name='profile'),
    path('logout', doLogout, name='logout'),
    path('add_to_profile/<str:recommendation>/', add_to_profile, name='add_to_profile'),
    path('delete_result/<int:result_id>/', delete_result, name='delete_result'),
path('show_all/', show_all, name='show_all'),
]



