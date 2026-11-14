# Калькулятор себестоимости и раскроя изделия

Веб-сервис для швейного цеха «М.и.Р.» (Сургут). Экспресс-расчёт себестоимости мерча и коммерческое предложение в PDF за 5–10 минут вместо нескольких часов.

Репозиторий: [mopchiktopchik2-cell/5-medvedey](https://github.com/mopchiktopchik2-cell/5-medvedey)

## Что умеет

- **Калькулятор пошива** — тип изделия, сложность, тираж, подкладка/капюшон/карманы → трудоёмкость и стоимость.
- **Калькулятор раскроя** — детали кроя с припусками, раскладка по ширине рулона, межлекальные отходы → метраж и стоимость материала + работа раскройщика.
- **Сводная смета** — материал + раскрой + пошив + фурнитура + брендирование, себестоимость единицы, срок изготовления.
- **КП в PDF** — реквизиты цеха, таблица расчёта, итоги, подпись; кириллица в шрифте PT Sans.
- **История расчётов** — поиск по номеру/изделию/подрядчику, фильтры по дате и типу изделия.
- **Справочники технолога** — ткани, фурнитура, брендирование, изделия, коэффициенты, нормо-часы.
- **Роли** — менеджер видит только свои расчёты, технолог — все и правит справочники.
- **Ссылка для подрядчика** — публичный просмотр сметы и скачивание PDF без входа.

## Роли и доступы

| Роль | Права | Демо-логин |
| --- | --- | --- |
| Менеджер | создаёт расчёты, видит только свои, скачивает PDF, делится ссылкой | `manager@mir.ru` / `manager123` |
| Технолог | всё выше + все расчёты + справочники и настройки | `technologist@mir.ru` / `technolog123` |

Демо-пользователи создаются автоматически при пустой базе (`SEED_DEMO_DATA=true`).

## Формулы расчёта

**Пошив**

```
трудоёмкость = базовое время изделия × коэффициент сложности × тираж
             × (подкладка ×1.15) × (капюшон ×1.10) × (карманы ×1.08)
стоимость    = трудоёмкость × нормо-час швеи
```

**Раскрой**

```
габарит детали = (длина + 2×припуск) × (ширина + 2×припуск), припуск по умолчанию 1.5 см
раскладка      = полосы по ширине рулона (next-fit decreasing height, поворот детали 90°)
длина кроя     = сумма высот полос
метраж         = длина / 100 × (1 + коэффициент отходов)
материал       = метраж × цена погонного метра
работа         = (деталей всего / норма выработки в час) × нормо-час раскройщика
```

**Остальное**

```
фурнитура «за штуку»    = цена × количество на изделие × тираж
фурнитура «на изделие»  = цена × тираж
брендирование           = цена за позицию × позиций × тираж
итого                   = материал + раскрой + пошив + фурнитура + брендирование
срок изготовления       = округление вверх(тираж / мощность цеха) + буфер, дней
```

Все деньги считаются в `Decimal`, округление до копеек — только на выводе.

## Стек

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0, SQLite (по умолчанию) / PostgreSQL, JWT в httpOnly cookie, argon2-хеши, fpdf2 для PDF.
- **Frontend:** React 19, TypeScript, Vite, React Router, oxlint.
- **Инфраструктура:** Docker Compose, GitHub Actions (ruff, pytest, oxlint, сборка).

## Структура

```
backend/
  app/
    calculators.py     чистые функции: раскладка, пошив, смета, сроки
    services.py        сборка расчёта из справочников
    models.py          SQLAlchemy-модели
    schemas.py         pydantic-контракты API
    security.py        JWT, роли, хеши
    pdf.py             генерация КП (PT Sans)
    seed.py            справочники и демо-пользователи
    routers/           auth, dictionaries, estimates, health
    assets/fonts/      PT Sans Regular/Bold + лицензия OFL
  tests/               28 тестов: формулы, API, права, PDF
frontend/
  src/
    pages/             вход, калькулятор, история, КП, справочники, публичная смета
    api.ts             типизированный клиент
    auth.tsx           контекст авторизации
docs/
  manager-guide.md     инструкция менеджера
  idea.md              описание кейса
```

## Запуск локально (Windows)

```powershell
git clone git@github.com:mopchiktopchik2-cell/5-medvedey.git
cd 5-medvedey
.\scripts\setup.ps1
.\scripts\dev.ps1
```

- Интерфейс: http://localhost:5173
- API и Swagger: http://localhost:8000/docs

Вручную:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

cd frontend
npm install
npm run dev
```

## Docker

```powershell
# SQLite
docker compose up --build

# PostgreSQL
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up --build
```

Интерфейс — http://localhost:5173, API — http://localhost:8000.

## Переменные окружения

Шаблон — `.env.example`. Секреты в git не попадают.

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `APP_ENV` | `development` | `production` включает secure-cookie |
| `DATABASE_URL` | `sqlite:///./data/app.db` | строка подключения SQLAlchemy |
| `CORS_ORIGINS` | `http://localhost:5173` | разрешённые источники через запятую |
| `SECRET_KEY` | dev-значение | подпись JWT, заменить в production |
| `ACCESS_TOKEN_TTL_MINUTES` | `720` | срок жизни сессии |
| `SEED_DEMO_DATA` | `true` | заполнение справочников при пустой базе |
| `VITE_API_URL` | пусто → `/api` | адрес API для фронтенда |

## API

| Метод | Путь | Доступ |
| --- | --- | --- |
| POST | `/api/auth/login` | все |
| POST | `/api/auth/logout` | авторизованные |
| GET | `/api/auth/me` | авторизованные |
| GET | `/api/dictionaries` | авторизованные |
| POST/PATCH | `/api/dictionaries/{fabrics,hardware,branding,product-types,complexity}` | технолог |
| PATCH | `/api/dictionaries/settings` | технолог |
| POST | `/api/estimates/preview` | авторизованные |
| POST | `/api/estimates` | авторизованные |
| GET | `/api/estimates` | авторизованные (менеджер — только свои) |
| GET | `/api/estimates/{id}` | владелец или технолог |
| DELETE | `/api/estimates/{id}` | владелец или технолог |
| GET | `/api/estimates/{id}/pdf` | владелец или технолог |
| POST | `/api/estimates/{id}/share` | владелец или технолог |
| GET | `/api/public/estimates/{token}` | без авторизации |
| GET | `/api/public/estimates/{token}/pdf` | без авторизации |

## Проверки

```powershell
cd backend
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\pytest.exe

cd ..\frontend
npm run lint
npm run build
```

Те же проверки выполняются в GitHub Actions (`.github/workflows/ci.yml`).

## Ограничения и планы

- Раскладка кроя — эвристика «полками» с поворотом деталей, а не полноценный оптимизатор вложенности. Для укрупнённого экспресс-расчёта этого достаточно; точный расклад даёт САПР.
- Отправка PDF на email не подключена: в интерфейсе есть публичная ссылка на смету и скачивание PDF. Для SMTP подготовлены переменные в `.env.example`.
- Логотип цеха в PDF пока не выводится — используется текстовый блок с названием и реквизитами.
- Схема БД создаётся автоматически (`create_all`); для продакшена стоит добавить Alembic.
- Автотесты фронтенда отсутствуют: сквозной сценарий проверялся вручную через headless-браузер.

## Лицензия

MIT — см. [LICENSE](LICENSE). Шрифт PT Sans распространяется по SIL OFL (`backend/app/assets/fonts/OFL.txt`).
