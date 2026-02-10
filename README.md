# domainac

Простой сервис на FastAPI для проверки домена: зарегистрирован он или нет.
Проверка работает по схеме: `RDAP` -> fallback `WHOIS`.

## Запуск в Docker

```bash
docker compose up --build
```

API будет доступен на `http://localhost:18080`.

Сервис использует нестандартный 5-значный порт `18080` и перед стартом всегда проверяет, что порт свободен.
Если порт занят, запуск завершается с ошибкой.

## Документация API

- Swagger UI: `http://localhost:18080/swagger`
- Swagger UI (стандартный URL FastAPI): `http://localhost:18080/docs`
- ReDoc: `http://localhost:18080/redoc`
- OpenAPI JSON: `http://localhost:18080/openapi.json`

## Запуск без Docker

```bash
python3 -m pip install -r requirements.txt
python3 -m app.run_server
```

По умолчанию используется `PORT=18080`. Можно переопределить:

```bash
PORT=19090 python3 -m app.run_server
```

## Примеры запросов

Проверка домена:

```bash
curl "http://localhost:18080/check?domain=example.com"
```

Массовая проверка:

```bash
curl -X POST "http://localhost:18080/check/batch" \
  -H "Content-Type: application/json" \
  -d '{"domains":["example.com","google.com","bad domain"]}'
```

Health-check:

```bash
curl "http://localhost:18080/health"
```

## Формат ответа

```json
{
  "domain": "example.com",
  "registered": true,
  "status": "registered",
  "error": null
}
```

`status` может быть:
- `registered`
- `unregistered`
- `unknown` (если WHOIS вернул неоднозначный ответ)
- `invalid` (только в массовой проверке, если домен невалидный)
