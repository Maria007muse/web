import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'holiday_choice_web.settings')
django.setup()

from travel_app.models import Destination
from sentence_transformers import SentenceTransformer
import numpy as np

def generate_embeddings():
    model = SentenceTransformer('all-MiniLM-L6-v2')
    destinations = Destination.objects.all()
    for dest in destinations:
        # Комбинируем текст для эмбеддинга
        text = f"{dest.country} {dest.season} {dest.activity_type} {dest.tags} {dest.description or ''} {dest.recommendation}"
        embedding = model.encode(text, convert_to_numpy=True).tolist()
        dest.embedding = embedding
        dest.save()
        print(f"Сгенерирован эмбеддинг для {dest.recommendation}")
    print("Генерация завершена")

if __name__ == "__main__":
    generate_embeddings()
