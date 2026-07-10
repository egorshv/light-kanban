# light-kanban

Лёгкий персональный kanban-трекер: доски → колонки → задачи + типизированные связи между задачами (`blocks`, `subtask_of`, `relates_to`, `duplicates`). Один пользователь, данные в одном файле SQLite, API-first. Полная документация — [docs.md](docs.md), план реализации — [implementation-plan.md](implementation-plan.md).

## Запуск (docker compose, ≤ 3 команды)

```sh
git clone <repo> && cd light-kanban
docker compose up --build
```

Открыть <http://localhost:8000>. База данных — `./data/kanban.db`; **бэкап = копия этого файла** (восстановление — положить копию обратно при остановленном контейнере).

### Токен доступа (опционально)

По умолчанию аутентификация выключена (локальный режим). Для self-hosted:

```sh
KANBAN_TOKEN=мой-секрет docker compose up --build
```

API ждёт заголовок `Authorization: Bearer <токен>`. Для UI один раз в консоли браузера: `localStorage.setItem('kanban_token', 'мой-секрет')`. HTTPS — забота вашего reverse-proxy.

## Переменные окружения

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `KANBAN_DB_PATH` | `kanban.db` (`/data/kanban.db` в docker) | путь к файлу SQLite |
| `KANBAN_TOKEN` | пусто | bearer-токен; пусто ⇒ auth выключена |
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
