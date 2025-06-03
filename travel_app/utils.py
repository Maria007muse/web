# Вспомогательные функции для views.py

from .models import UserProfile
from .forms import ReviewForm


def handle_review_form(request, destination, user_review=None):
    form = ReviewForm(request.POST)
    if user_review:
        return False, "Отзыв уже добавлен."

    if form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.destination = destination
        review.save()
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        user_profile.add_review(review)
        return True, None

    error = next(iter(form.errors.values()), ["Пожалуйста, заполните форму корректно."])[0]
    return False, error


def calculate_ratings(reviews):
    from django.db.models import Avg
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    rounded_average_rating = round(average_rating)
    average_stars = [True if i <= rounded_average_rating else False for i in range(1, 6)]
    reviews_with_stars = [
        (review, [True if i <= review.rating else False for i in range(1, 6)])
        for review in reviews
    ]
    return average_rating, average_stars, reviews_with_stars
