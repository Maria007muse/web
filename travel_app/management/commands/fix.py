from django.core.management.base import BaseCommand
from travel_app.models import Destination

class Command(BaseCommand):
    help = 'Fix season data in Destination model'

    def handle(self, *args, **kwargs):
        season_mapping = {
            'З': 'Зима',
            'В': 'Весна',
            'О': 'Осень',
            'Л': 'Лето',
            'К': 'Круглый год'
        }
        for dest in Destination.objects.all():
            old_season = dest.season
            if old_season in season_mapping:
                dest.season = season_mapping[old_season]
                dest.save()
                self.stdout.write(f"Updated ID {dest.id}: {old_season} -> {dest.season}")
            elif old_season and old_season not in [choice[0] for choice in Destination.SEASON_CHOICES]:
                dest.season = ''
                dest.save()
                self.stdout.write(f"Cleared invalid season for ID {dest.id}: {old_season}")
