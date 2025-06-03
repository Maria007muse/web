import hashlib
import json

from django.contrib.auth.models import User
from django.db import models


class ActivityType(models.Model):
    ACTIVITY_CHOICES = [
        ("Горнолыжный", "Горнолыжный"),
        ("Культурный", "Культурный"),
        ("Пляжный", "Пляжный"),
        ("Гастрономический", "Гастрономический"),
        ("Экотуризм", "Экотуризм"),
        ("Шопинг", "Шопинг"), # нет в бд
        ("Приключенческий", "Приключенческий"),# нет в бд
    ]
    name = models.CharField(max_length=30, unique=True, choices=ACTIVITY_CHOICES)

    def __str__(self):
        return self.name


class Language(models.Model):
    LANGUAGE_CHOICES = [
        ("Английский", "Английский"),
        ("Русский", "Русский"),
        ("Французский", "Французский"),
        ("Немецкий", "Немецкий"),
        ("Испанский", "Испанский"),
        ("Итальянский", "Итальянский"),
        ("Португальский", "Португальский"),
        ("Арабский", "Арабский"),
        ("Китайский", "Китайский"),
        ("Японский", "Японский"),
        ("Другое", "Другое"),
    ]
    name = models.CharField(max_length=30, unique=True, choices=LANGUAGE_CHOICES)

    def __str__(self):
        return self.name


class Tag(models.Model):
    TAG_CHOICES = [
        ("Романтика", "Романтика"),
        ("Активный отдых", "Активный отдых"),
        ("Природа", "Природа"),
        ("Городской отдых", "Городской отдых"),
        ("Релакс", "Релакс"),
    ]
    name = models.CharField(max_length=30, unique=True, choices=TAG_CHOICES)

    def __str__(self):
        return self.name


class Vibe(models.Model):
    VIBE_CHOICES = [
        ("Европейская классика", "Европейская классика"),
        ("Современный мегаполис", "Современный мегаполис"),
        ("Азиатская культура", "Азиатская культура"),
        ("Средневековая архитектура", "Средневековая архитектура"),
        ("Восточная экзотика", "Восточная экзотика"),
        ("Деревенский уют", "Деревенский уют"),
        ("Горы и природа", "Горы и природа"),
        ("Морской курорт", "Морской курорт"),
        ("Пустыня и приключения", "Пустыня и приключения"),
    ]
    name = models.CharField(max_length=50, unique=True, choices=VIBE_CHOICES)

    def __str__(self):
        return self.name


class ComfortLevel(models.Model):
    COMFORT_CHOICES = [
        ("Бюджетный", "Бюджетный"),
        ("Средний", "Средний"),
        ("Люкс", "Люкс"),
    ]
    name = models.CharField(max_length=30, unique=True, choices=COMFORT_CHOICES)

    def __str__(self):
        return self.name


class DestinationImage(models.Model):
    destination = models.ForeignKey('Destination', on_delete=models.CASCADE, related_name='additional_images')
    image = models.ImageField(upload_to='destination_additional_images/')

    def __str__(self):
        return f"Image for {self.destination.recommendation}"


class Destination(models.Model):
    CLIMATE_CHOICES = [
        ("Жаркий и сухой", "Жаркий и сухой"),
        ("Жаркий и влажный", "Жаркий и влажный"),
        ("Тёплый и умеренный", "Тёплый и умеренный"),
        ("Прохладный и свежий", "Прохладный и свежий"),
        ("Пасмурный и дождливый", "Пасмурный и дождливый"), #нет в бд
        ("Холодный и снежный", "Холодный и снежный"),
    ]
    SEASON_CHOICES = [
        ("Зима", "Зима"),
        ("Весна", "Весна"),
        ("Лето", "Лето"),
        ("Осень", "Осень"),
    ]

    country = models.CharField(max_length=100, blank=True)
    climate = models.CharField(max_length=30, choices=CLIMATE_CHOICES)
    activity_types = models.ManyToManyField(ActivityType, blank=True, related_name='destinations')
    season = models.CharField(max_length=50, choices=SEASON_CHOICES, blank=True)
    vibe = models.ManyToManyField(Vibe, blank=True, related_name='destinations')
    comfort_level = models.ManyToManyField(ComfortLevel, blank=True, related_name='destinations')
    family_friendly = models.BooleanField(default=False)
    visa_required = models.BooleanField(default=False)
    language = models.ManyToManyField(Language, blank=True, related_name='destinations')
    tags = models.ManyToManyField(Tag, blank=True, related_name='destinations')
    is_popular = models.BooleanField(default=False)
    image = models.ImageField(upload_to='destination_images/')
    recommendation = models.CharField(max_length=255, default="")
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.recommendation


class UserInteraction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, null=True, blank=True)
    interaction_type = models.CharField(
        max_length=20,
        choices=[
            ('view', 'Просмотр'),
            ('favorite', 'Избранное'),
            ('review', 'Отзыв'),
            ('search', 'Поиск')
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    search_filters = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.destination.recommendation if self.destination else 'No destination'} - {self.interaction_type}"


class Result(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recommendation = models.CharField(max_length=255, default="")

    def __str__(self):
        return self.recommendation


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    results = models.ManyToManyField('Result', blank=True)
    reviews = models.ManyToManyField('Review', blank=True, related_name='profile_reviews')

    def add_result(self, destination):
        result = Result.objects.create(user=self.user, recommendation=destination.recommendation)
        self.results.add(result)

    def delete_result(self, result_id):
        result = Result.objects.get(id=result_id)
        self.results.remove(result)

    def add_review(self, review):
        self.reviews.add(review)

    def delete_review(self, review_id):
        review = Review.objects.get(id=review_id)
        self.reviews.remove(review)

    def __str__(self):
        return self.user.username


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    destination = models.ForeignKey(Destination, related_name='reviews', on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.destination.recommendation}'


class RelevanceScore(models.Model):
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE)
    filters_hash = models.CharField(max_length=255)  # Хэш комбинации фильтров
    score = models.FloatField()  # Оценка релевантности (0–100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.destination.recommendation} - {self.score}%"

    @staticmethod
    def generate_filters_hash(filters):
        """Генерирует хэш для комбинации фильтров."""
        sorted_filters = sorted({k: str(v) for k, v in filters.items() if v}.items())
        filters_str = json.dumps(sorted_filters, ensure_ascii=False)
        return hashlib.md5(filters_str.encode('utf-8')).hexdigest()
