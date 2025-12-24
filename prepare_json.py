# prepare_json.py
import json

# Укажите путь к вашему service-account.json
with open('service-account.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Минифицируем в одну строку
minified = json.dumps(data, separators=(',', ':'), ensure_ascii=False)

print("="*80)
print("Скопируйте эту строку в Railway переменную GOOGLE_SERVICE_ACCOUNT_JSON:")
print("="*80)
print(minified)
print("="*80)

# Также сохраним в файл для удобства
with open('service-account-minified.txt', 'w', encoding='utf-8') as f:
    f.write(minified)
print("\n✅ Также сохранено в файл: service-account-minified.txt")