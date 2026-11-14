# 5 медведей

Проект для хакатона. Репозиторий: [mopchiktopchik2-cell/5-medvedey](https://github.com/mopchiktopchik2-cell/5-medvedey).

Рабочий каркас: FastAPI + SQLite на бэкенде, React + TypeScript (Vite) на фронтенде, тесты, линтеры, Docker и CI.

> Сейчас внутри демонстрационный CRUD «заметки» — он нужен, чтобы весь стек работал от запуска до деплоя. Когда определится идея, заменяем сущность `Note` на модели проекта: `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/routers/notes.py`, `frontend/src/api.ts`.

## Структура

```
.
├── backend/                FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── config.py       настройки из .env
│   │   ├── db.py           движок и сессии SQLite
│   │   ├── models.py       модели БД
│   │   ├── schemas.py      pydantic-схемы
│   │   ├── main.py         приложение, CORS, роутеры
│   │   └── routers/        health, notes
│   ├── tests/              pytest
│   ├── Dockerfile
│   └── requirements*.txt
├── frontend/               React + TS + Vite
│   ├── src/
│   │   ├── api.ts          клиент к API
│   │   ├── App.tsx         интерфейс
│   │   └── index.css
│   ├── Dockerfile
│   └── nginx.conf
├── docs/idea.md            описание идеи проекта
├── scripts/                setup.ps1, dev.ps1
├── .github/workflows/ci.yml
└── docker-compose.yml
```

## Быстрый старт (Windows)

```powershell
git clone git@github.com:mopchiktopchik2-cell/5-medvedey.git
cd 5-medvedey
.\scripts\setup.ps1   # .env, venv, зависимости
.\scripts\dev.ps1     # два окна: API и фронтенд
```

- API: http://localhost:8000 (Swagger — `/docs`)
- Фронтенд: http://localhost:5173

Вручную:

```powershell
# бэкенд
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# фронтенд (второй терминал)
cd frontend
npm install
npm run dev
```

## Docker

```powershell
docker compose up --build
```

- Фронтенд: http://localhost:5173
- API: http://localhost:8000

## API

| Метод | Путь | Описание |
| --- | --- | --- |
| GET | `/api/health` | проверка живости |
| GET | `/api/notes` | список записей |
| POST | `/api/notes` | создать (`title`, `body`) |
| GET | `/api/notes/{id}` | одна запись |
| PATCH | `/api/notes/{id}` | частично обновить |
| DELETE | `/api/notes/{id}` | удалить |

## Проверки

```powershell
# бэкенд
cd backend
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\pytest.exe

# фронтенд
cd frontend
npm run lint
npm run build
```

То же самое гоняется в GitHub Actions на каждый push и pull request — `.github/workflows/ci.yml`.

## Переменные окружения

Шаблон — `.env.example`, реальные значения — в `.env` (в git не попадает).

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `APP_ENV` | `development` | режим работы |
| `APP_PORT` | `8000` | порт API |
| `DATABASE_URL` | `sqlite:///./data/app.db` | подключение к БД |
| `CORS_ORIGINS` | `http://localhost:5173` | разрешённые источники (через запятую) |
| `VITE_API_URL` | пусто → `/api` | адрес API для фронтенда |

## Команда

| Роль | Участник |
| --- | --- |
| — | — |

## Лицензия

MIT — см. [LICENSE](LICENSE).
