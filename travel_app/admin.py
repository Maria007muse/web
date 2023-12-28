from django.contrib import admin
from travel_app.models import Destination, Result

class DestinationAdmin(admin.ModelAdmin):
    list_display = ('climate', 'activity_type', 'budget', 'popularity', 'cultural_diversity')
    list_filter = ('climate', 'activity_type', 'budget', 'popularity', 'cultural_diversity')
    search_fields = ('climate', 'activity_type', 'budget', 'popularity', 'cultural_diversity')

admin.site.register(Destination, DestinationAdmin)
admin.site.register(Result)

