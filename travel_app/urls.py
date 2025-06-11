# urls.py
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
    path('create-post/', create_inspiration_post, name='create_inspiration_post'),
    path('inspiration_feed/', inspiration_feed, name='inspiration_feed'),
    path('delete_post/<int:pk>/', delete_post, name='delete_post'),
    path('save_post/<int:pk>/', save_inspiration_post, name='save_post'),
    path('remove_saved_post/<int:pk>/', remove_saved_post, name='remove_saved_post'),
    path('toggle_like_post/<int:pk>/', toggle_like_post, name='toggle_like_post'),
path('route/create/', create_route, name='create_route'),
    path('route/<int:route_id>/', route_detail, name='route_detail'),
    path('route/<int:route_id>/edit/', edit_route, name='edit_route'),  # Новый маршрут для редактирования
    path('reorder_route_points/<int:route_id>/', reorder_route_points, name='reorder_route_points'),
    path('route/<int:route_id>/delete/', delete_route, name='delete_route'),
    path('route_point/<int:point_id>/delete/', delete_route_point, name='delete_route_point'),
]
