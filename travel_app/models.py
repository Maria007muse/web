from django.contrib.auth.models import User
from django.db import models


class Destination(models.Model):
    CLIMATE_CHOICES = [("Умеренный", "Умеренный"), ("Холодный", "Холодный"), ("Теплый", "Теплый")]
    ACTIVITY_CHOICES = [("Горнолыжный", "Горнолыжный"), ("Культурный", "Культурный"), ("Пляжный", "Пляжный")]
    BUDGET_CHOICES = [("От 300000 руб", "От 300000 руб"), ("От 100000 до 300000 руб", "От 100000 до 300000 руб"),
                      ("До 100000 руб", "До 100000 руб")]
    POPULARITY_CHOICES = [("Низкая", "Низкая"), ("Высокая", "Высокая")]
    DIVERSITY_CHOICES = [("Большое", "Большое"), ("Умеренное", "Умеренное"), ("Незначительное", "Незначительное")]

    climate = models.CharField(max_length=30, choices=CLIMATE_CHOICES)
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_CHOICES)
    budget = models.CharField(max_length=30, choices=BUDGET_CHOICES)
    popularity = models.CharField(max_length=30, choices=POPULARITY_CHOICES)
    cultural_diversity = models.CharField(max_length=30, choices=DIVERSITY_CHOICES)

    image = models.ImageField(upload_to='destination_images/')
    recommendation = models.CharField(max_length=255, default="")

    def __str__(self):
        return self.recommendation


class Result(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recommendation = models.CharField(max_length=255, default="")

    def __str__(self):
        return self.recommendation

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    results = models.ManyToManyField('Result', blank=True)

    def add_result(self, destination):
        result = Result.objects.create(user=self.user, recommendation=destination.recommendation)
        self.results.add(result)

    def delete_result(self, result_id):
        result = Result.objects.get(id=result_id)
        self.results.remove(result)

    def __str__(self):
        return self.user.username


