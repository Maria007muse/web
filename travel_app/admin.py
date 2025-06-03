from django.contrib import admin
from .models import Destination, Result, ActivityType, Language, Tag, Vibe, ComfortLevel, DestinationImage

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

# Обновлённая админка для Destination
@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = (
        'recommendation', 'country', 'climate', 'season', 'is_popular',
        'get_activity_types', 'get_languages', 'get_tags', 'get_vibes', 'get_comfort_levels'
    )
    list_filter = (
        'country', 'climate', 'season', 'is_popular', 'activity_types', 'language', 'tags', 'vibe', 'comfort_level'
    )
    search_fields = ('title', 'country', 'recommendation', 'description')
    inlines = [ActivityTypeInline, LanguageInline, TagInline, VibeInline, ComfortLevelInline, DestinationImageInline]

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

admin.site.register(Result)
