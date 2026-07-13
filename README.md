# light-kanban

Лёгкий kanban-трекер: доски → колонки → задачи + типизированные связи между задачами (`blocks`, `subtask_of`, `relates_to`, `duplicates`). Мультипользовательский (у каждого — свои доски), данные в одном файле SQLite, API-first. Полная документация — [docs.md](docs.md), план реализации — [implementation-plan.md](implementation-plan.md).

## Запуск (docker compose, ≤ 3 команды)

```sh
git clone <repo> && cd light-kanban
KANBAN_JWT_SECRET=$(openssl rand -hex 32) docker compose up --build
```

Открыть <http://localhost:8000>. База данных — `./data/kanban.db`; **бэкап = копия этого файла** (восстановление — положить копию обратно при остановленном контейнере).

### Аутентификация

Вход обязателен: регистрация по email+паролю либо вход через Google. API выдаёт JWT (`POST /api/v1/auth/register|login` → `{token, user}`), дальше — заголовок `Authorization: Bearer <token>`. Срок жизни токена — `KANBAN_JWT_TTL` (по умолчанию 24 ч), по истечении UI выбрасывает на экран входа. HTTPS — забота вашего reverse-proxy.

**Вход через Google**: создайте OAuth-клиент (тип «Web application») в [Google Cloud Console](https://console.cloud.google.com/apis/credentials), в Authorized redirect URIs добавьте `{origin}/api/v1/auth/google/callback` (для dev — `http://localhost:5173/api/v1/auth/google/callback`), задайте `GOOGLE_CLIENT_ID` и `GOOGLE_CLIENT_SECRET`. Без них кнопка Google возвращает 404.

**Миграция со старой (одно­пользовательской) версии**: существующие доски остаются без владельца и не видны никому. После регистрации присвойте их себе:

```sh
sqlite3 data/kanban.db "UPDATE boards SET owner_id=(SELECT id FROM users WHERE email='вы@пример.ru') WHERE owner_id IS NULL"
```

## Переменные окружения

Шаблон — [.env.example](.env.example): скопируйте в `.env`, docker compose подхватит автоматически.

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `KANBAN_DB_PATH` | `kanban.db` (`/data/kanban.db` в docker) | путь к файлу SQLite |
| `KANBAN_JWT_SECRET` | — (обязательна) | секрет подписи JWT (HS256) |
| `KANBAN_JWT_TTL` | `86400` | срок жизни токена, секунд |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | пусто | OAuth-клиент Google; пусто ⇒ вход через Google отключён |
| `GOOGLE_REDIRECT_URI` | `{origin}/api/v1/auth/google/callback` | callback, если origin за прокси не определяется сам |
| `KANBAN_LOG_LEVEL` | `INFO` | уровень структурных JSON-логов |
| `KANBAN_STATIC_DIR` | `frontend/dist` | каталог собранной SPA |

## API

REST JSON под `/api/v1` (контракт — docs.md §6). Интерактивная OpenAPI-документация: <http://localhost:8000/docs>.

## Разработка

Требуются [uv](https://docs.astral.sh/uv/) и Node 22+.

```sh
make dev        # бэкенд :8000 (--reload) + фронтенд :5173 (vite, proxy /api)
make test       # unit- и contract-тесты бэкенда (pytest)
make lint       # ruff + tsc
make build      # сборка фронтенда в frontend/dist
make e2e        # Playwright против приложения на :8000
```

Для `make e2e` приложение должно быть запущено с собранным фронтендом: `docker compose up --build`, либо `make build && make dev-backend`.

Слои бэкенда (ADR-001/006): `api/` — тонкие роутеры, `services/` — вся доменная логика, `repo/` — только SQL. Будущий MCP-сервер (этап 2) вызывает сервисный слой напрямую.
