# Калькулятор себестоимости и раскроя изделия

Веб-сервис для швейного цеха «М.и.Р.» (Сургут). Экспресс-расчёт себестоимости мерча и коммерческое предложение в PDF за 5–10 минут вместо нескольких часов.

Репозиторий: [mopchiktopchik2-cell/5-medvedey](https://github.com/mopchiktopchik2-cell/5-medvedey)

## Ожидаемый результат

Что заказчик получает по итогам работы и где это проверить:

| Результат | Где |
| --- | --- |
| Сервис, доступный по внутренней сети или закрытому URL | `.\scripts\start-lan.ps1` → `http://<IP>:8080`; боевой контур — раздел «Развёртывание на хостинге в РФ» |
| Заполненные справочники (10 тканей, 5 фурнитуры, 4 изделия) | `backend/app/seed.py`, закреплено тестом `backend/tests/test_seed.py` |
| Инструкция менеджеру | [`docs/manager-guide.md`](docs/manager-guide.md) |
| Исходный код с комментариями и инструкцией по развёртыванию | этот README и каталог [`docs/`](docs/) |
| Расчёт себестоимости и PDF за 5–10 минут | сценарий с таймингом — [`docs/demo-script.md`](docs/demo-script.md) |

Сопоставление всех пяти пунктов с реализацией и приёмочный чек-лист — в [`docs/acceptance.md`](docs/acceptance.md).

## Что умеет

- **Калькулятор пошива** — тип изделия, сложность, тираж, подкладка/капюшон/карманы → трудоёмкость и стоимость.
- **Калькулятор раскроя** — детали кроя с припусками, раскладка по ширине рулона, межлекальные отходы → метраж и стоимость материала + работа раскройщика.
- **Сводная смета** — материал + раскрой + пошив + фурнитура + брендирование, себестоимость единицы, срок изготовления.
- **КП в PDF** — реквизиты цеха, таблица расчёта, итоги, подпись; кириллица в шрифте PT Sans.
- **Логотип цеха** — технолог загружает PNG/JPEG/WebP, логотип выводится в шапке PDF и на публичной странице.
- **История расчётов** — поиск по номеру/изделию/подрядчику, фильтры по дате и типу изделия, экспорт в CSV, подгрузка страницами.
- **Справочники технолога** — ткани, фурнитура, брендирование, изделия, коэффициенты, нормо-часы. Загрузка прайса из CSV: шаблон, UTF-8/Windows-1251, частичный импорт с отчётом об ошибках.
- **Профили подрядчиков** — название, email для КП и телефон; подрядчик сохраняется в истории расчётов, email подставляется в отправку.
- **Роли** — менеджер видит только свои расчёты, технолог — все и правит справочники.
- **Сотрудники и пароли** — технолог заводит сотрудников, отключает уволенных и сбрасывает забытые пароли; каждый сотрудник меняет свой пароль сам. Смена или сброс пароля, а также смена роли завершают все сессии сотрудника на всех устройствах.
- **Ссылка для подрядчика** — публичный просмотр сметы и скачивание PDF без входа. Ссылка живёт 30 дней (настраивается) и в любой момент отзывается; во внешнем ответе нет email и ФИО сотрудника, нормо-часов и цены погонного метра.
- **Защита от перебора пароля** — после нескольких неудачных попыток вход с этого адреса временно блокируется.
- **Отправка КП на email** — PDF вложением через SMTP; без SMTP письмо сохраняется в `outbox` как `.eml`.
- **Повтор расчёта** — сохранённая смета открывается в калькуляторе со всеми параметрами.
- **Черновик расчёта** — параметры автоматически сохраняются в браузере и переживают обрыв связи.

## Роли и доступы

| Роль | Права | Демо-логин |
| --- | --- | --- |
| Менеджер | создаёт расчёты, видит только свои, скачивает PDF, делится ссылкой, меняет свой пароль | `manager@mir.ru` / `manager123` |
| Технолог | всё выше + все расчёты + справочники и настройки + управление сотрудниками | `technologist@mir.ru` / `technolog123` |

Демо-пользователи создаются только при `SEED_DEMO_DATA=true` и пустой базе. В production демо-данные выключены: первого технолога создаёт администратор командой

```powershell
python -m app.cli create-user --email boss@example.ru --name "Иванов И. И."
```

Пароль команда спросит интерактивно (или примите `--password`). Сбросить забытый пароль без входа в систему: `python -m app.cli reset-password --email manager@mir.ru`.

Сотрудники и пароли: технолог открывает «Справочники → Пользователи», заводит сотрудника, меняет роль, отключает уволенного и задаёт новый пароль. Отключить или понизить собственную учётную запись нельзя, как и оставить систему без активного технолога. Свой пароль сотрудник меняет по ссылке «Сменить пароль» в шапке; после смены нужно войти заново.

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

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0, SQLite (по умолчанию) / PostgreSQL, JWT в httpOnly cookie, argon2-хеши, fpdf2 для PDF, Alembic для миграций.
- **Frontend:** React 19, TypeScript, Vite, React Router, oxlint, vitest, Playwright (сквозной E2E).
- **Инфраструктура:** Docker Compose, Caddy (HTTPS), GitHub Actions (ruff, pytest, проверка миграций, oxlint, vitest, сборка, E2E на Docker-стенде).

## Интерфейс

Светлая редакционная тема: белый фон, волосяные рамки, острые углы и оранжевый акцент. Заголовки — Onest, акцентный курсив — Playfair Display, служебные подписи и цифры — Roboto Mono, текст — Manrope.

Шрифты самохостингуются в `frontend/public/fonts` и не зависят от внешних CDN. Лицензии и источники — в [`frontend/public/fonts/NOTICE.md`](frontend/public/fonts/NOTICE.md).

## Структура

```
backend/
  app/
    calculators.py     чистые функции: раскладка, пошив, смета, сроки
    services.py        сборка расчёта из справочников
    models.py          SQLAlchemy-модели
    schemas.py         pydantic-контракты API
    security.py        JWT, роли, хеши
    ratelimit.py       блокировка входа после неудачных попыток
    pdf.py             генерация КП (PT Sans)
    branding.py        логотип цеха: валидация, нормализация, хранение
    mailer.py          отправка КП по SMTP с фолбэком в outbox
    seed.py            справочники и демо-пользователи
    cli.py             создание сотрудника и сброс пароля без входа
    routers/           auth, users, dictionaries, estimates, branding, health
    assets/fonts/      PT Sans Regular/Bold + лицензия OFL
  migrations/          Alembic: baseline-миграция и окружение
  alembic.ini
  entrypoint.sh        миграции + запуск uvicorn в контейнере
  tests/               75 тестов: формулы, API, права, PDF, email, CSV, логотип,
                       подрядчики, сотрудники, публичные ссылки, rate-limit,
                       справочники, отзыв сессий и идемпотентность сида
frontend/
  public/fonts/        self-hosted шрифты интерфейса (OFL / Apache 2.0)
  src/
    pages/             вход, калькулятор, история, КП, справочники, профиль, публичная смета
    components/        шапка, карточка сотрудников
    index.css          тема интерфейса и адаптив
    fonts.css          @font-face для локальных шрифтов
    api.ts             типизированный клиент
    auth.tsx           контекст авторизации
    format.ts          форматирование чисел, денег и дат
    format.test.ts     unit-тесты форматтеров (vitest)
scripts/
  setup.ps1            установка зависимостей и генерация SECRET_KEY
  dev.ps1              запуск бэкенда и фронтенда
  start-lan.ps1        запуск в Docker для внутренней сети (порт 8080)
  stop-lan.ps1         остановка LAN-стенда
  backup.ps1           резервная копия базы, логотипа и outbox
  restore.ps1          восстановление из архива
  check_migrations.py  проверка сценариев миграций
docs/
  manager-guide.md     инструкция менеджера
  technologist-guide.md инструкция технолога
  demo-script.md       сценарий показа на 5–6 минут
  video-storyboard.md  раскадровка видео-гайда на 2–3 минуты
  acceptance.md        приёмка: пять результатов и чек-лист
  requirements-checklist.md  матрица соответствия ТЗ
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

`setup.ps1` создаёт `.env` из шаблона и генерирует в нём случайный `SECRET_KEY`. Без `.env` в development работает небезопасный дефолтный ключ, а в production приложение намеренно не запустится.

Вручную:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload

cd frontend
npm install
npm run dev
```

Схема базы обновляется миграциями Alembic. Приложение по-прежнему вызывает `create_all` при старте — это страховка для чистой локальной базы, миграции её не ломают. Для рабочих контуров миграции применяются явно: `alembic upgrade head`.

## Docker

```powershell
# один раз: .env со случайным SECRET_KEY
Copy-Item .env.example .env
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))" | Add-Content .env

# SQLite
docker compose up --build

# PostgreSQL
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up --build
```

Интерфейс — http://localhost:5173, API — http://localhost:8000.

Compose намеренно безопасен по умолчанию: `APP_ENV=production`, демо-данные не создаются, без `SECRET_KEY` контейнер не стартует. Значения `APP_ENV` и `SEED_DEMO_DATA` в compose зафиксированы, чтобы локальный `.env` не включал демо-режим на сервере. После первого запуска создайте технолога:

```powershell
docker compose exec backend python -m app.cli create-user --email boss@example.ru --name "Иванов И. И."
```

Если нужен демо-стенд с учётками `manager@mir.ru` / `technologist@mir.ru`, не меняйте боевой `docker-compose.yml` — используйте LAN-режим из следующего раздела: приложение предупредит в логах, что демо-пароли доступны всем.

Контейнер бэкенда при старте выполняет `alembic upgrade head` (см. `backend/entrypoint.sh`), поэтому схема обновляется сама. Вариант с PostgreSQL проверен: схема, демо-данные, расчёт, профили подрядчиков и PDF работают без изменений в коде.

## Пилот во внутренней сети

Режим для цеха и показа заказчику: HTTP без TLS, фронтенд на порту **8080**, демо-справочники и учётки включены.

```powershell
.\scripts\start-lan.ps1   # собрать и запустить, выдаст адрес в локальной сети
.\scripts\stop-lan.ps1    # остановить, данные сохранятся
```

Скрипт сам создаёт `.env`, генерирует `SECRET_KEY`, поднимает стек и печатает адрес вида `http://192.168.1.42:8080`. Демо-доступы: `manager@mir.ru` / `manager123` и `technologist@mir.ru` / `technolog123`.

С другого компьютера сайт открывается по этому адресу. Если не открывается — разрешите порт 8080 в брандмауэре Windows от имени администратора:

```powershell
New-NetFirewallRule -DisplayName "5-medvedey LAN" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow
```

Этот режим **не для публичного интернета**: cookie передаются без `Secure`, а демо-пароли известны. Для внешнего доступа используйте раздел ниже и обязательно TLS.

Без Docker, в режиме разработки, наружу можно выйти так: `uvicorn app.main:app --host 0.0.0.0` и `npm run dev -- --host`, затем открыть `http://<IP>:5173`.

## Резервное копирование

```powershell
.\scripts\backup.ps1                  # архив в backups\
.\scripts\backup.ps1 -OutDir D:\bkp   # в другую папку
.\scripts\restore.ps1 -Archive .\backups\5-medvedey-20261114-203556.zip
```

`backup.ps1` сам определяет режим:

- **PostgreSQL в Docker** — `pg_dump`;
- **SQLite в Docker** — согласованный снимок через `sqlite3 backup`, сервис останавливать не нужно;
- **локальный запуск** — снимок `backend/data/app.db`.

В архив попадают база, `uploads/` (логотип) и `outbox/` (письма без SMTP), а также `manifest.txt` с режимом и коммитом. Восстановление останавливает backend, подменяет базу и запускает его снова; текущая база сохраняется рядом как `app.db.before-restore-<дата>`.

Копии делайте по расписанию и храните хотя бы одну вне сервера. На Linux те же действия доступны без PowerShell:

```bash
# SQLite
docker compose exec -T backend python -c "import sqlite3; s=sqlite3.connect('/app/data/app.db'); d=sqlite3.connect('/app/data/backup.db'); s.backup(d); d.close(); s.close()"
docker compose cp backend:/app/data/backup.db ./backup.db

# PostgreSQL
docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db pg_dump -U mir -d mir > backup.sql
```

## Развёртывание на хостинге в РФ

Сервис хранит базу, PDF и загруженный логотип только на вашем сервере и не обращается к внешним облачным API. Подойдёт VPS в российском дата-центре: Timeweb Cloud, Selectel, Yandex Cloud или аналогичный.

1. Создайте сервер с Docker и Docker Compose, направьте домен на его IP.
2. Задайте переменные окружения: `DOMAIN=mir.example.ru`, `APP_ENV=production`, стойкий `SECRET_KEY` (без него приложение не стартует), `POSTGRES_PASSWORD`, `CORS_ORIGINS=https://mir.example.ru`, `SEED_DEMO_DATA=false`.
3. Запустите PostgreSQL-вариант с автоматическим HTTPS:

   ```powershell
   docker compose -f docker-compose.yml -f docker-compose.postgres.yml -f docker-compose.caddy.yml up -d --build
   ```

4. Создайте первого технолога: `docker compose exec backend python -m app.cli create-user --email boss@example.ru --name "Иванов И. И."`.
5. Caddy из `docker-compose.caddy.yml` сам получит сертификат Let's Encrypt и будет проксировать `https://ваш-домен` на `frontend:80`. Наружу открыты только 80 и 443; порты frontend и backend не публикуются. Заголовки безопасности и CSP заданы в `Caddyfile`.
6. Настройте резервное копирование (`.\scripts\backup.ps1` по планировщику или `pg_dump` в cron) и мониторинг доступности `/api/health`.

Схема базы обновляется миграциями Alembic при старте контейнера. Откат baseline-миграции на базе с данными запрещён намеренно — чтобы случайно не удалить справочники и историю расчётов.

Если TLS временно нет и сервис работает по HTTP, secure-cookie сломают вход. На это время задайте `COOKIE_SECURE=false` и как можно скорее включите HTTPS.

SMTP можно указать любого российского провайдера (Яндекс 360, Mail.ru для бизнеса, Timeweb) — достаточно заполнить переменные `SMTP_*`.

## Переменные окружения

Шаблон — `.env.example`. Секреты в git не попадают.

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `APP_ENV` | `development` | `production` запрещает слабый `SECRET_KEY` и включает secure-cookie |
| `DATABASE_URL` | `sqlite:///./data/app.db` | строка подключения SQLAlchemy |
| `POSTGRES_PASSWORD` | `mir` | пароль PostgreSQL для compose-оверрайда |
| `CORS_ORIGINS` | `http://localhost:5173` | разрешённые источники через запятую |
| `SECRET_KEY` | dev-значение | подпись JWT; в production обязателен случайный ключ длиной от 32 символов |
| `ACCESS_TOKEN_TTL_MINUTES` | `720` | срок жизни сессии |
| `COOKIE_SECURE` | авто | `true`/`false` жёстко задаёт secure-cookie; пусто — включать только в production |
| `SEED_DEMO_DATA` | `true` (в compose — `false`) | заполнение справочников и демо-учёток при пустой базе |
| `SHARE_TOKEN_TTL_DAYS` | `30` | срок жизни публичной ссылки на КП |
| `LOGIN_MAX_ATTEMPTS` | `5` | неудачных попыток входа до блокировки |
| `LOGIN_LOCKOUT_MINUTES` | `15` | на сколько минут блокируется вход |
| `SMTP_HOST` | пусто | SMTP-сервер; пока пусто, письма пишутся в `data/outbox` |
| `SMTP_PORT` | `465` | порт SMTP |
| `SMTP_USER` / `SMTP_PASSWORD` | пусто | логин и пароль SMTP |
| `SMTP_FROM` | пусто | адрес отправителя (по умолчанию `SMTP_USER`) |
| `SMTP_USE_SSL` | `true` | SSL с первого байта (порт 465); для 587 — `false` |
| `SMTP_STARTTLS` | `false` | поднять STARTTLS после подключения |
| `SMTP_TIMEOUT_SECONDS` | `15` | таймаут соединения с SMTP |
| `OUTBOX_DIR` | `./data/outbox` | куда складывать `.eml`, если SMTP не настроен |
| `UPLOADS_DIR` | `./data/uploads` | хранение логотипа цеха |
| `VITE_API_URL` | пусто → `/api` | адрес API для фронтенда |

## API

| Метод | Путь | Доступ |
| --- | --- | --- |
| POST | `/api/auth/login` | все |
| POST | `/api/auth/logout` | авторизованные |
| GET | `/api/auth/me` | авторизованные |
| POST | `/api/auth/change-password` | авторизованные (свой пароль) |
| GET | `/api/users` | технолог |
| POST | `/api/users` | технолог |
| PATCH | `/api/users/{id}` | технолог (роль, ФИО, активность, пароль) |
| GET | `/api/dictionaries` | авторизованные |
| POST/PATCH | `/api/dictionaries/{fabrics,hardware,branding,product-types,complexity}` | технолог |
| POST/PATCH | `/api/contractors` | технолог |
| PATCH | `/api/dictionaries/settings` | технолог |
| POST | `/api/dictionaries/logo` | технолог (multipart, PNG/JPEG/WebP ≤ 2 МБ) |
| DELETE | `/api/dictionaries/logo` | технолог |
| POST | `/api/estimates/preview` | авторизованные |
| POST | `/api/estimates` | авторизованные |
| GET | `/api/estimates` | авторизованные (менеджер — только свои) |
| GET | `/api/estimates/export.csv` | авторизованные (те же фильтры и права) |
| GET | `/api/estimates/{id}` | владелец или технолог |
| DELETE | `/api/estimates/{id}` | владелец или технолог |
| GET | `/api/estimates/{id}/pdf` | владелец или технолог |
| POST | `/api/estimates/{id}/share` | владелец или технолог (выдаёт ссылку со сроком) |
| DELETE | `/api/estimates/{id}/share` | владелец или технолог (отзывает ссылку) |
| POST | `/api/estimates/{id}/send-email` | владелец или технолог |
| GET | `/api/public/estimates/{token}` | без авторизации |
| GET | `/api/public/estimates/{token}/pdf` | без авторизации |
| GET | `/api/public/logo` | без авторизации |
| GET | `/api/public/logo/meta` | без авторизации |

## Проверки

```powershell
cd backend
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\pytest.exe
.\.venv\Scripts\python.exe ..\scripts\check_migrations.py

cd ..\frontend
npm run lint
npm test
npm run build
```

`check_migrations.py` проверяет пять сценариев: чистая база, повторный `upgrade`, база от старого `create_all`, база без `share_expires_at` и база без `token_version`.

Те же проверки выполняются в GitHub Actions (`.github/workflows/ci.yml`).

Сквозной сценарий (вход → смета → история → PDF → импорт CSV) проверяется в настоящем браузере:

```powershell
.\scripts\start-lan.ps1   # стенд на http://localhost:8080
cd frontend
npm run test:e2e
```

E2E использует установленный Microsoft Edge (канал `msedge`) и не скачивает браузеры на машине разработчика. В GitHub Actions отдельная job `e2e` поднимает LAN-стенд в Docker, ставит Chromium (`npx playwright install --with-deps chromium`), ждёт `/api/health` и запускает те же сценарии на чистой базе. При падении в артефакты попадают отчёт Playwright, скриншоты и логи контейнеров.

## Ограничения и планы

- Раскладка кроя — эвристика «полками» с поворотом деталей, а не полноценный оптимизатор вложенности. Для укрупнённого экспресс-расчёта этого достаточно; точный расклад даёт САПР.
- Если SMTP не настроен, письмо с КП не отправляется, а сохраняется в `data/outbox/*.eml` — файл можно открыть почтовым клиентом. Это осознанный демо-фолбэк, а не ошибка. Реальная отправка через SMTP требует рабочих учётных данных и в CI не проверяется.
- Счётчик неудачных входов хранится в памяти процесса: при нескольких воркерах uvicorn лимит действует на каждый процесс отдельно. Для одного контейнера этого достаточно; при масштабировании лимит лучше вынести на reverse proxy или в Redis.
- Смена пароля, сброс пароля технологом и смена роли увеличивают `users.token_version` и отзывают все ранее выданные JWT. Просто истёкшие сессии доживают до конца срока (12 часов) — отдельного «выйти на всех устройствах» без смены пароля нет.
- SQLite оставлен вариантом по умолчанию для локальной демонстрации. Для рабочего контура используйте PostgreSQL-оверрайд: он проверен и описан выше.
- Автотесты фронтенда покрывают форматтеры (`format.test.ts`), а не сквозные сценарии в браузере. Полный сценарий «ввод → расчёт → КП» проверялся вручную.

## Лицензия

MIT — см. [LICENSE](LICENSE). Шрифт PT Sans распространяется по SIL OFL (`backend/app/assets/fonts/OFL.txt`).
