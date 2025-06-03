from django.urls import path
from .views import *

urlpatterns = [
    path('', home, name='index'),
    path('search/', search, name='search'),
    path('login', loginPage, name='login'),
    path('register', registerPage, name='register'),
    path('profile/', profile, name='profile'),
    path('logout', doLogout, name='logout'),
    path('add_to_profile/<str:recommendation>/', add_to_profile, name='add_to_profile'),
    path('delete_result/<int:result_id>/', delete_result, name='delete_result'),
    path('destination/<int:pk>/', destination_detail, name='destination_detail'),
    path('show_all/', show_all, name='show_all'),
    path('destination/<int:pk>/review/', add_review, name='add_review'),
    path('delete_review/<int:pk>/', delete_review, name='delete_review'),
    path('destination/<int:pk>/toggle_favorite/', toggle_favorite, name='toggle_favorite'),
    path('chatbot/', chatbot, name='chatbot'),
]
