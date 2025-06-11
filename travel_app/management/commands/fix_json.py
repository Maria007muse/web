import json

# Читаем файл как бинарный, чтобы вручную обработать BOM
with open('data.json', 'rb') as f:
    raw_data = f.read()
    # Пропускаем BOM (2 байта для UTF-16LE: FF FE)
    if raw_data.startswith(b'\xff\xfe'):
        text = raw_data[2:].decode('Windows-1251')
    else:
        text = raw_data.decode('Windows-1251')  # Если BOM нет

# Парсим JSON
data = json.loads(text)

# Сохраняем в UTF-8
with open('../../../data_fixed.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)
