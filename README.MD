# Project_store — Log Max Russia

Учебный интернет-магазин лесозаготовительной техники на Django и Django REST Framework. Проект содержит сайт с сессионной авторизацией и корзиной, а также REST API с JWT и Swagger.

Обязательные требования описаны в [техническом задании](06%20Project%20M3-1.md). Учебный ориентир — [M4PyHuntersProject, ветка dev](https://github.com/sounditbox/M4PyHuntersProject/tree/dev).

## Возможности

- Каталог активных товаров с поиском по названию и описанию, фильтрами категории и цены, пагинацией.
- Сортировка по цене, новизне и популярности. Популярность — сумма проданных единиц в заказах `paid`, `shipped`, `delivered`.
- Карточка товара с изображением, описанием, остатком, характеристиками и средним рейтингом через `Avg`. Без отзывов сайт показывает «Нет оценок», API возвращает `null`.
- Сессионная корзина: добавление, изменение количества, удаление, проверка доступности и точный расчёт стоимости через `Decimal`.
- Регистрация, вход, выход и личный кабинет. Корзина сохраняется после входа; пользователь видит только свои заказы.
- Оформление заказа с адресом доставки и двумя условными способами оплаты. Реального списания денег нет.
- Атомарное создание заказа и списание остатков с блокировкой строк PostgreSQL. Цены сохраняются в позициях заказа.
- Отмена собственного заказа в статусе `pending` с однократным возвратом остатков.
- Отзывы только после покупки со статусом `delivered`: один отзыв пользователя на товар, целая оценка от 1 до 5.
- Django Admin для категорий, товаров, заказов, отзывов и стандартных пользователей. Заказы нельзя физически удалить через админку.
- Публичный API товаров, JWT-защищённый API заказов и OpenAPI/Swagger.

## Технологии и версии

Точные версии зависимостей зафиксированы в [uv.lock](uv.lock), ограничения — в [pyproject.toml](pyproject.toml).

| Компонент | Версия |
|---|---|
| Python локальной проверенной среды | 3.14.5; проект требует Python >= 3.14 |
| Django | 6.1 |
| Django REST Framework | 3.18.0 |
| djangorestframework-simplejwt | 5.5.1 |
| drf-spectacular | 0.30.0 |
| PostgreSQL | 17, образ `postgres:17-alpine` |
| psycopg / psycopg-binary | 3.3.5 |
| Pillow | 12.3.0 |
| python-dotenv | 1.2.3, устанавливается через зависимость `dotenv` |
| pytest / pytest-django | 9.2.0 / 4.14.0, группа `dev` |

Менеджер зависимостей — uv. Dockerfile использует `python:3.14-slim-bookworm`: патч-версия Python в контейнере может отличаться от локальной. Образ uv берётся с тегом `latest`.

## Структура

```text
config/                 Настройки Django, корневые URL, WSGI и ASGI
products/               Category, Product, каталог, карточка, фильтры и админка
shop/                   Сессионная корзина, регистрация, личный кабинет и тесты
orders/                 Order, OrderItem, checkout, статусы, отмена и админка
reviews/                Review, ModelForm отзыва, ограничения и админка
api/                    Сериализаторы, ViewSet, router, JWT и тесты API
templates/              Общие компоненты, страницы корзины, авторизации и заказов
static/                 Подключаемые CSS, JavaScript и изображения
media/                  Изображения, загруженные через приложение; не хранятся в Git
manage.py               Команды Django
pyproject.toml          Зависимости и настройки pytest
uv.lock                 Зафиксированные зависимости
Dockerfile              Образ приложения
docker-compose.yml      Приложение и PostgreSQL
docker-compose.local.yml  Только PostgreSQL для локальной разработки
.env.example            Шаблон переменных окружения
```

`shop` подключается через URL и использует модели других приложений; собственных моделей и таблиц у него нет. В `templates/templates/` и `templates/static/` остаются исходные материалы вёрстки. Основная статика подключается из корневой `static/`.

## Требования и получение проекта

Для локального Django нужны Git, uv, Python 3.14 и Docker с Compose для PostgreSQL. Для полного Docker-сценария достаточно Git и Docker Compose; Python и uv внутри образа устанавливаются Dockerfile.

Установите uv по [официальной инструкции](https://docs.astral.sh/uv/getting-started/installation/). Docker Engine должен быть запущен. Проверьте, что порты `8000` и `5433` свободны.

```powershell
git clone --branch dev https://github.com/tsypnyatov-sergey/Project_store.git
cd Project_store
```

Все дальнейшие команды выполняются из корня проекта, рядом с `manage.py`. Примеры команд рассчитаны на PowerShell.

Для локальной разработки установите зависимости из lock-файла:

```powershell
uv sync --locked --python 3.14.5
```

Группа `dev`, включая pytest, устанавливается по умолчанию. Команды `uv run` используют окружение проекта, поэтому отдельно активировать `.venv` не требуется.

## Переменные окружения

Не публикуйте рабочие `.env` и `.env.local`. Они исключены из Git и Docker-контекста. `.env.example` содержит только шаблон; Django автоматически его не читает.

В новой копии создайте два рабочих файла. Если файлы уже существуют, сохраните их настройки и не перезаписывайте:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
if (!(Test-Path .env.local)) { Copy-Item .env.example .env.local }
```

Заполните их самостоятельно. Ниже приведены только примеры конфигурации, а не действующие секреты.

**`.env` — для контейнеров:**

```dotenv
SECRET_KEY=replace_with_generated_secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=project_store
POSTGRES_USER=project_store
POSTGRES_PASSWORD=replace_with_generated_password
```

**`.env.local` — для Django на компьютере:**

```dotenv
SECRET_KEY=replace_with_generated_secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_DB=project_store
POSTGRES_USER=project_store
POSTGRES_PASSWORD=replace_with_generated_password
```

Замените обе заглушки секретов. Имя БД, пользователь и пароль должны совпадать в двух файлах, если оба сценария используют одну БД. Случайное значение для ключа можно получить локально после установки зависимостей:

```powershell
uv run python -c "import secrets; print(secrets.token_hex(32))"
```

Не используйте приведённые заглушки как пароль или ключ. `DEBUG=True` здесь нужен для учебного запуска с обслуживанием статики и media через Django; это не production-конфигурация.

### Как выбираются настройки

- `config/settings.py` вызывает `load_dotenv('.env.local')`, затем читает `os.getenv()`.
- При локальном запуске используется `.env.local`. `.env` сам Django не загружает.
- Переменные, уже заданные в терминале или IDE, имеют приоритет: `load_dotenv()` по умолчанию не перезаписывает окружение.
- Оба Compose-файла передают `.env` контейнеру PostgreSQL через `env_file`.
- Основной Compose также передаёт `.env` сервису `web`. Явный `environment` у `web` устанавливает `POSTGRES_HOST=postgres` и `POSTGRES_PORT=5432` поверх `env_file`.
- Файлы `.env` и `.env.local` не копируются и не монтируются в контейнер. Compose передаёт их значения как переменные процесса; отсутствие `.env.local` внутри образа ожидаемо.
- Автоматическое чтение `.env` для подстановок Compose и `env_file: .env` — разные механизмы. Аргумент Compose `--env-file` сам по себе не заменяет явно записанный `env_file`.

| Соединение | Адрес и порт |
|---|---|
| Django на компьютере → PostgreSQL | `127.0.0.1:5433` |
| Django в `web` → PostgreSQL | `postgres:5432` |
| Внутри PostgreSQL-контейнера | `5432` |

Проброс `5433:5432` означает внешний порт компьютера слева и внутренний порт контейнера справа. `localhost` внутри `web` указывает на сам `web`, а не на PostgreSQL.

## Сценарий 1: Django локально, PostgreSQL в Docker

Подготовьте оба env-файла и зависимости, затем запустите только БД:

```powershell
docker compose -f docker-compose.local.yml up -d postgres
docker compose -f docker-compose.local.yml ps
```

Дождитесь состояния PostgreSQL `healthy`. Файл `docker-compose.local.yml` выбирается явно через `-f`; он не запускает Django.

```powershell
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Откройте [каталог](http://127.0.0.1:8000/) и [админку](http://127.0.0.1:8000/admin/). Остановка локального Django — `Ctrl+C`.

Для остановки БД без удаления контейнера и volume:

```powershell
docker compose -f docker-compose.local.yml stop postgres
```

## Сценарий 2: Django и PostgreSQL в Docker

Заполните `.env` и запустите из корня проекта:

```powershell
docker compose up --build
```

Compose выбирает `docker-compose.yml`, ждёт готовности PostgreSQL, выполняет миграции и запускает Django на `0.0.0.0:8000`. Каталог доступен по адресу [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

В другом терминале из корня проекта создайте администратора:

```powershell
docker compose exec web python manage.py createsuperuser
```

Миграции выполняются автоматически при старте `web`. Для явного повторного запуска существующей команды:

```powershell
docker compose exec web python manage.py migrate
```

Остановка сервисов без удаления данных:

```powershell
docker compose stop
```

Не запускайте одновременно локальный Django и контейнер `web` на порту `8000`. Оба Compose-файла объявляют сервис `postgres` и volume `pgdata`; при одинаковом имени Compose-проекта они используют общую БД. Это альтернативные сценарии запуска, а не две независимые базы.

В Dockerfile зависимости устанавливаются с `--no-dev`, поэтому pytest в образ приложения не включён. Для pytest используйте локальное окружение из первого сценария.

## Первое наполнение и работа магазина

Новая БД не содержит демонстрационных товаров. Войдите в админку и создайте категории и товары: задайте цену, активность, положительный остаток и, при необходимости, изображение. Названия `Category` и `Product` пока вводите на английском языке — Unicode-slug отложен.

Основные страницы:

| URL | Назначение |
|---|---|
| `/`, `/products/` | Каталог |
| `/product/<slug>/` | Карточка товара и отзывы |
| `/cart/` | Корзина |
| `/checkout/` | Оформление заказа после входа |
| `/account/register/`, `/account/login/` | Регистрация и вход |
| `/account/` | Собственные заказы |
| `/orders/<id>/` | Детали собственного заказа и POST-отмена |
| `/admin/` | Администрирование |

В веб-каталоге категория передаётся как slug в `categories`; параметры поиска и цен — `search`, `min_price`, `max_price`. Значения `sorting`: `price`, `-price`, `-created_at`, `popularity`. Ссылки пагинации сохраняют GET-параметры.

Новый заказ получает `pending`. Пользователь может отменить только свой `pending`-заказ. Администратор меняет статусы по цепочкам:

```text
pending → paid → shipped → delivered
pending → cancelled
paid    → cancelled
```

`delivered` и `cancelled` — конечные статусы. При отмене остатки возвращаются только один раз. Для проверки отзывов создайте покупку и переведите её через админку в `delivered`; затем войдите покупателем и отправьте отзыв на странице товара.

## REST API и JWT

Сайт использует стандартные Django-сессии. API заказов требует JWT: вход в браузере сам по себе не даёт доступа к нему. Корзина доступна только на сайте; API создаёт заказ из переданного `items`, независимо от сессии.

| Метод | URL | Доступ |
|---|---|---|
| GET | `/api/products/` | Публичный список активных товаров |
| GET | `/api/products/<id>/` | Публичная карточка активного товара |
| POST | `/api/token/` | Получение access/refresh по имени и паролю |
| POST | `/api/token/refresh/` | Обновление access через refresh |
| GET, POST | `/api/orders/` | Список своих заказов / создание, JWT |
| GET | `/api/orders/<id>/` | Свой заказ, JWT |
| POST | `/api/orders/<id>/cancel/` | Отмена своего pending-заказа, JWT |
| GET | `/api/schema/` | OpenAPI-схема |
| GET | `/api/docs/` | Swagger UI |

API товаров поддерживает `search`, `category` (ID, не slug), `min_price`, `max_price`, `page`. Размер страницы — 6. Списки имеют поля `count`, `next`, `previous`, `results`. Для неактивного или отсутствующего товара возвращается 404; некорректные фильтры дают 400.

### Примеры запросов в PowerShell

Каталог и деталь товара — используйте существующие ID из своей БД:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/products/?search=Machine&min_price=0&page=1'
Invoke-RestMethod 'http://127.0.0.1:8000/api/products/?category=1&max_price=1000'
Invoke-RestMethod 'http://127.0.0.1:8000/api/products/1/'
```

Создайте пользователя через сайт. Для получения JWT введите его данные в запросе ниже. Значения-заглушки не являются действующими учётными данными:

```powershell
$credentials = @{ username = 'YOUR_USERNAME'; password = 'YOUR_PASSWORD' } | ConvertTo-Json
$tokens = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/token/' -ContentType 'application/json' -Body $credentials
$headers = @{ Authorization = "Bearer $($tokens.access)" }
Invoke-RestMethod 'http://127.0.0.1:8000/api/orders/' -Headers $headers
```

Создание заказа:

```powershell
$orderBody = @{
    items = @(@{ product_id = 1; quantity = 2 })
    shipping_address = 'YOUR_DELIVERY_ADDRESS'
    payment_method = 'cash'
} | ConvertTo-Json -Depth 4
$order = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/orders/' -Headers $headers -ContentType 'application/json' -Body $orderBody
Invoke-RestMethod "http://127.0.0.1:8000/api/orders/$($order.id)/" -Headers $headers
```

`items` должен быть непустым, без повторных товаров; количество — положительное целое число. Способы оплаты: `cash` — наличными при получении, `card` — картой при получении. Цена каждой позиции копируется из БД. Автор, итог и статус вычисляются сервером; переданные клиентом значения этих полей не используются.

Отмена и обновление токена:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/orders/$($order.id)/cancel/" -Headers $headers
$refreshBody = @{ refresh = $tokens.refresh } | ConvertTo-Json
$accessResponse = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/token/refresh/' -ContentType 'application/json' -Body $refreshBody
$headers = @{ Authorization = "Bearer $($accessResponse.access)" }
```

Ошибки данных и недопустимая отмена возвращают 400, отсутствие/ошибка JWT — 401, чужой или отсутствующий заказ — 404. POST/PUT/PATCH/DELETE товаров и PUT/PATCH/DELETE заказов недоступны. Отмена выполняется только отдельным POST-запросом. Токены не публикуйте и не сохраняйте в Git.

### Swagger и проверка схемы

Откройте [Swagger UI](http://127.0.0.1:8000/api/docs/), выполните `POST /api/token/`, скопируйте `access` и вставьте его в **Authorize** без префикса `Bearer`. Публичные товары можно запрашивать без токена, заказы — после авторизации.

Проверка генерации схемы без сохранения файла:

```powershell
uv run python manage.py spectacular --validate --fail-on-warn
```

Команда выводит схему в терминал. Swagger загружает JS/CSS с CDN, поэтому браузеру нужен доступ к интернету.

## Тесты и проверки

Используйте локальное uv-окружение и работающий PostgreSQL из первого сценария. Пользователь PostgreSQL должен иметь право создавать тестовую БД; пользователь, созданный стандартным PostgreSQL-образом при первой инициализации, такое право имеет.

Запускайте runner'ы последовательно: оба используют тестовую БД, отдельную от рабочей.

```powershell
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py test
uv run pytest -q
uv lock --check
```

Настройки pytest находятся в `pyproject.toml`: `DJANGO_SETTINGS_MODULE=config.settings`, файлы `tests.py`, `test_*.py`, `*_test.py`. Существующие Django `TestCase`, `TransactionTestCase` и DRF `APITestCase` выполняются обоими runner'ами без переписывания на фикстуры.

На текущем этапе оба runner'а выполняют 77 тестов. Pytest дополнительно сообщает о 44 успешных вложенных `subTest`. Проверяются каталог, корзина, авторизация, права доступа, заказы, конкуренция за последний товар, отзывы, API, JWT и OpenAPI. Процент покрытия не измерен.

## Ограничения текущей реализации

- Это учебная конфигурация: `runserver` и `DEBUG=True` не подходят для публичного production-развёртывания. HTTPS, безопасные cookies и отдельная раздача статики для production не настроены.
- **Для `media` нет отдельного volume.** В Docker загруженные изображения находятся в файловой системе `web` и могут потеряться при пересоздании контейнера. БД хранится отдельно в `pgdata`; это не сохраняет изображения.
- **PostgreSQL опубликован через `5433:5432` без ограничения адресом `127.0.0.1`.** В зависимости от настроек Docker и сети порт может быть доступен другим компьютерам. Это нужно учитывать при запуске вне локальной учебной среды.
- **Загрузка `.env.local` зависит от рабочей директории.** Запускайте команды из корня проекта; путь пока не привязан к `BASE_DIR`.
- Env-файлы не синхронизируются автоматически. Переменные IDE/терминала могут перекрыть файл; проверяйте источник параметров при ошибках подключения.
- Изменение пароля в `.env` не меняет автоматически пароль уже инициализированной БД в существующем volume. Не удаляйте volume ради исправления подключения.
- Теги Docker-образов не закреплены по digest. Сборка может получить другую патч-версию Python или uv; зависимости Python при этом берутся из `uv.lock`.
- Полная Docker-сборка ранее прерывалась ошибками дисковой среды; успешный запуск чистой копии через Compose требует отдельной проверки. Прохождение локальных тестов не является подтверждением Docker-сборки.
- Каталог в новой БД пуст; fixtures с техникой не добавлены. Товары и изображения вводятся через админку.
- Поддержка кириллических slug отложена. Названия категорий и товаров пока вводятся на английском языке.
- В checkout сейчас собирается адрес, но нет отдельного поля контактного телефона/email. Реальная оплата не выполняется.
- В проекте остаются старые материалы вёрстки, неиспользуемые участки JS и страница `guides-recipes` о пивоварении. Они не являются готовыми функциями магазина техники.
- Расширенный профиль, GraphQL, API отзывов, email-уведомления, аналитика админки и CI/CD не реализованы и не заявляются как готовые возможности.

## Чек-лист текущего этапа

- [x] Каталог, поиск, фильтры, сортировка и пагинация.
- [x] Карточка товара, средний рейтинг и отзывы после доставленной покупки.
- [x] Сессионная корзина и проверка остатков.
- [x] Атомарное оформление, снимки цен, переходы статусов и отмена.
- [x] Регистрация, сессионный вход/выход, собственные заказы.
- [x] Настроенная админка с запретом удаления заказов.
- [x] REST API товаров и заказов, JWT, OpenAPI/Swagger.
- [x] Миграции и ограничения БД в репозитории.
- [x] Django test runner и pytest-django на PostgreSQL.
- [x] Инструкции по окружению, запуску и API.
- [ ] Подтвердить запуск чистой копии через Docker Compose после устранения проблем дисковой среды.
- [ ] Завершить проверку контактных данных checkout и оставшихся материалов вёрстки перед сдачей.
