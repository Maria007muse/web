from django.contrib import admin
from django.urls import reverse
from django.http import HttpResponseRedirect
from django import forms
from .models import Destination, Result, ActivityType, Language, Tag, Vibe, ComfortLevel, DestinationImage, PendingDestination, InspirationPost

# Кастомная форма для DestinationAdmin
class DestinationAdminForm(forms.ModelForm):
    class Meta:
        model = Destination
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        pending_data = self.request.session.get('pending_destination_data', {}) if self.request else {}
        if pending_data:
            # Предзаполняем ManyToMany поля
            if pending_data.get('tags'):
                try:
                    self.initial['tags'] = Tag.objects.filter(name__in=pending_data['tags']).values_list('id', flat=True)
                except Tag.DoesNotExist:
                    pass  # Игнорируем, если теги не найдены
            if pending_data.get('vibe'):
                try:
                    self.initial['vibe'] = Vibe.objects.filter(name__in=pending_data['vibe']).values_list('id', flat=True)
                except Vibe.DoesNotExist:
                    pass  # Игнорируем, если vibe не найдены

# Инлайн для удобного редактирования связанных моделей
class ActivityTypeInline(admin.TabularInline):
    model = Destination.activity_types.through
    extra = 1

class LanguageInline(admin.TabularInline):
    model = Destination.language.through
    extra = 1

class TagInline(admin.TabularInline):
    model = Destination.tags.through
    extra = 1

class VibeInline(admin.TabularInline):
    model = Destination.vibe.through
    extra = 1

class ComfortLevelInline(admin.TabularInline):
    model = Destination.comfort_level.through
    extra = 1

class DestinationImageInline(admin.TabularInline):
    model = DestinationImage
    extra = 1

# Регистрация моделей
@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Vibe)
class VibeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(ComfortLevel)
class ComfortLevelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    form = DestinationAdminForm
    list_display = (
        'recommendation', 'country', 'climate', 'season', 'is_popular',
        'get_activity_types', 'get_languages', 'get_tags', 'get_vibes', 'get_comfort_levels'
    )
    list_filter = (
        'country', 'climate', 'season', 'is_popular', 'activity_types', 'language', 'tags', 'vibe', 'comfort_level'
    )
    search_fields = ('recommendation', 'country', 'description')
    inlines = [ActivityTypeInline, LanguageInline, TagInline, VibeInline, ComfortLevelInline, DestinationImageInline]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.request = request
        return form

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        pending_data = request.session.get('pending_destination_data', {})
        initial.update({
            'recommendation': pending_data.get('recommendation', ''),
            'country': pending_data.get('country', ''),
            'description': pending_data.get('description', ''),
            'climate': pending_data.get('climate', ''),
            'season': pending_data.get('season', ''),
            'tags': pending_data.get('tags', []),  # Подставляем ID тегов
            'vibe': pending_data.get('vibe', []),  # Подставляем ID атмосферы
        })
        print("Initial form data:", initial)  # Отладка: какие данные подставляются в форму
        return initial

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        pending_data = request.session.get('pending_destination_data', {})
        if pending_data.get('image'):
            DestinationImage.objects.create(destination=obj, image=pending_data['image'])

    def get_activity_types(self, obj):
        return ", ".join([a.name for a in obj.activity_types.all()])
    get_activity_types.short_description = 'Активности'

    def get_languages(self, obj):
        return ", ".join([l.name for l in obj.language.all()])
    get_languages.short_description = 'Языки'

    def get_tags(self, obj):
        return ", ".join([t.name for t in obj.tags.all()])
    get_tags.short_description = 'Теги'

    def get_vibes(self, obj):
        return ", ".join([v.name for v in obj.vibe.all()])
    get_vibes.short_description = 'Атмосфера'

    def get_comfort_levels(self, obj):
        return ", ".join([c.name for c in obj.comfort_level.all()])
    get_comfort_levels.short_description = 'Уровень комфорта'

@admin.register(PendingDestination)
class PendingDestinationAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'city', 'user', 'status', 'created_at')
    list_filter = ('status', 'country', 'created_at')
    search_fields = ('name', 'country', 'city')
    actions = ['approve_destinations', 'reject_destinations', 'create_destination']

    def approve_destinations(self, request, queryset):
        for pending in queryset:
            try:
                destination = pending.approve_to_destination()
                InspirationPost.objects.filter(pending_destination=pending).update(
                    destination=destination,
                    pending_destination=None
                )
                self.message_user(request, f"Место '{pending.name}' одобрено и добавлено в Destination.")
            except ValueError as e:
                self.message_user(request, f"Ошибка для '{pending.name}': {str(e)} Перенаправление на форму создания.", level='error')
                request.session['pending_destination_data'] = {
                    'recommendation': pending.name,
                    'country': pending.country,
                    'description': pending.description or '',
                    'climate': pending.climate,
                    'season': pending.season,
                    'tags': list(pending.tags.values_list('id', flat=True)),  # Передаем ID тегов
                    'vibe': list(pending.vibe.values_list('id', flat=True)),  # Передаем ID атмосферы
                    'image': pending.image.url if pending.image else None,
                }
                return HttpResponseRedirect(reverse('admin:travel_app_destination_add'))
        self.message_user(request, f"Выбранные места одобрены и добавлены в Destination.")
    approve_destinations.short_description = "Одобрить и добавить в Destination"

    def create_destination(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Выберите ровно одно место для создания Destination.", level='error')
            return
        pending = queryset.first()
        tags_ids = list(pending.tags.values_list('id', flat=True))  # Передаем ID тегов
        vibe_ids = list(pending.vibe.values_list('id', flat=True))  # Передаем ID атмосферы
        print("PendingDestination tags IDs:", tags_ids)  # Отладка
        print("PendingDestination vibe IDs:", vibe_ids)  # Отладка
        request.session['pending_destination_data'] = {
            'recommendation': pending.name,
            'country': pending.country,
            'description': pending.description or '',
            'climate': pending.climate,
            'season': pending.season,
            'tags': tags_ids,  # Передаем ID тегов
            'vibe': vibe_ids,  # Передаем ID атмосферы
            'image': pending.image.url if pending.image else None,
        }
        return HttpResponseRedirect(reverse('admin:travel_app_destination_add'))
    create_destination.short_description = "Создать Destination из выбранного места"


admin.site.register(Result)
admin.site.register(InspirationPost)
