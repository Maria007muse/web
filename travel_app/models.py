from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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


class InspirationPost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, null=True, blank=True)
    pending_destination = models.ForeignKey('PendingDestination', on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='inspiration_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, blank=True)
    vibe = models.ManyToManyField(Vibe, blank=True)
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)

    def __str__(self):
        if self.destination:
            return f"{self.user.username} - {self.destination.recommendation}"
        return f"{self.user.username} - {self.pending_destination.name if self.pending_destination else 'No destination'}"


class PendingDestination(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    CLIMATE_CHOICES = Destination.CLIMATE_CHOICES
    SEASON_CHOICES = Destination.SEASON_CHOICES
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    description = models.TextField()  # Убери blank=True, чтобы сделать обязательным
    image = models.ImageField(upload_to='pending_destination_images/', blank=True, null=True)
    climate = models.CharField(max_length=30, choices=CLIMATE_CHOICES, blank=True, null=True)
    season = models.CharField(max_length=50, choices=SEASON_CHOICES, blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)
    vibe = models.ManyToManyField(Vibe, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def approve_to_destination(self):
        if not all([self.name, self.description, self.image, self.climate, self.season]):
            missing_fields = []
            if not self.name:
                missing_fields.append("название")
            if not self.description:
                missing_fields.append("описание")
            if not self.image:
                missing_fields.append("изображение")
            if not self.climate:
                missing_fields.append("климат")
            if not self.season:
                missing_fields.append("сезон")
            raise ValueError(
                f"Невозможно создать Destination: отсутствуют обязательные поля: {', '.join(missing_fields)}.")
        destination = Destination.objects.create(
            recommendation=self.name,
            country=self.country,
            description=self.description,
            climate=self.climate,
            season=self.season,
            image=self.image,
        )
        tags = self.tags.all()
        vibe = self.vibe.all()
        print("Copying tags:", tags)  # Отладка: какие теги копируются
        print("Copying vibe:", vibe)  # Отладка: какая атмосфера копируется
        destination.tags.set(tags)
        destination.vibe.set(vibe)
        self.status = 'approved'
        self.save()
        return destination


class UserInteraction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, null=True, blank=True)
    post = models.ForeignKey(InspirationPost, on_delete=models.CASCADE, null=True, blank=True)
    interaction_type = models.CharField(
        max_length=20,
        choices=[
            ('view', 'Просмотр места'),
            ('favorite', 'Избранное'),
            ('review', 'Отзыв'),
            ('search', 'Поиск'),
            ('view_post', 'Просмотр поста'),
            ('save_post', 'Сохранение поста'),
            ('like_post', 'Лайк поста'),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    search_filters = models.JSONField(null=True, blank=True)
    post_filters = models.JSONField(null=True, blank=True)

    def __str__(self):
        if self.destination:
            return f"{self.user.username} - {self.destination.recommendation} - {self.interaction_type}"
        elif self.post:
            return f"{self.user.username} - Post {self.post.id} - {self.interaction_type}"
        return f"{self.user.username} - No destination - {self.interaction_type}"


class Result(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recommendation = models.CharField(max_length=255, default="")

    def __str__(self):
        return self.recommendation


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    results = models.ManyToManyField('Result', blank=True)
    reviews = models.ManyToManyField('Review', blank=True, related_name='profile_reviews')
    posts = models.ManyToManyField('InspirationPost', blank=True, related_name='user_posts')
    saved_inspiration_posts = models.ManyToManyField('InspirationPost', blank=True, related_name='saved_by_users')
    routes = models.ManyToManyField('Route', blank=True, related_name='user_routes')

    def add_route(self, route):
        self.routes.add(route)

    def remove_route(self, route_id):
        route = Route.objects.get(id=route_id)
        self.routes.remove(route)

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

    def add_post(self, post):
        self.posts.add(post)

    def delete_post(self, post_id):
        post = InspirationPost.objects.get(id=post_id)
        self.posts.remove(post)

    def add_saved_post(self, post):
        self.saved_inspiration_posts.add(post)

    def remove_saved_post(self, post_id):
        post = InspirationPost.objects.get(id=post_id)
        self.saved_inspiration_posts.remove(post)

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

# models.py (только изменённые модели)
class Route(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='routes')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} by {self.user.username}"

class RoutePoint(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='points')
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, null=True, blank=True)
    custom_name = models.CharField(max_length=255, blank=True)
    note = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    date_time = models.DateTimeField(null=True, blank=True)  # Добавляем поле из предыдущих форм

    class Meta:
        ordering = ['order']

    def clean(self):
        if not self.destination and not self.custom_name:
            raise ValidationError('Укажите место из списка или задайте своё название.')
        if self.destination and self.custom_name:
            raise ValidationError('Выберите только одно: место из списка или своё название.')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.custom_name or (self.destination.recommendation if self.destination else "Custom Point")
