import requests

# Настройки
city = "Париж"
country = "Франция"
keywords = ["туризм", "климат", "достопримечательности", "отдых"]  # или: ["туризм", "климат", "отдых", "достопримечательности"]
query = f"{city} {country} " + ", ".join(keywords)

url = "https://real-time-web-search.p.rapidapi.com/search-advanced-v2"
querystring = {
    "q": query,
    "fetch_ai_overviews": "false",
    "num": "5",     # Кол-во результатов
    "start": "0",
    "gl": "ru",     # Гео-локация поиска: "ru", "us", "fr" и т.д.
    "hl": "ru",     # Язык поиска: "ru" или "en"
    "nfpr": "0"
}

headers = {
    "x-rapidapi-key": "e2788d8fe3msh024a048dc2e12ebp1f2ca4jsnc6f88a5e903a",  # Твой ключ
    "x-rapidapi-host": "real-time-web-search.p.rapidapi.com"
}

# Запрос
print(f"🔍 Запрос: {query}")
print("📡 Отправка запроса...")

try:
    response = requests.get(url, headers=headers, params=querystring)
    response.raise_for_status()
    print("✅ Запрос выполнен успешно.")
except requests.exceptions.HTTPError as err:
    print("❌ Ошибка HTTP:", err)
    print("Ответ:", response.text)
    exit()
except Exception as e:
    print("❌ Общая ошибка:", e)
    exit()

# Парсинг
data = response.json()
results = data.get("data", {}).get("organic_results", [])


if not results:
    print("⚠️ Нет результатов в 'organic'. Полный ответ:")
    print(data)
    exit()

snippets = []
for i, res in enumerate(results):
    title = res.get("title", "Без заголовка")
    snippet = res.get("snippet", "Нет описания")
    url_result = res.get("url", "—")
    print(f"\n🔹 [{i + 1}] {title}\n{snippet}\n🔗 {url_result}")
    snippets.append(snippet)

# Объединённый текст
full_text = " ".join(snippets)
if full_text.strip():
    print("\n📌 Объединённый текст для GPT:")
    print(full_text[:1000], "..." if len(full_text) > 1000 else "")
else:
    print("⚠️ Не удалось собрать текст.")
