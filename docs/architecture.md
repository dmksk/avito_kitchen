# Архитектура и пользовательские сценарии

## C4 Container diagram

```mermaid
flowchart LR
    user["Пользователь<br/>Web-клиент"]
    restaurant["Сотрудник заведения"]
    main["Main Service<br/>FastAPI :8000"]
    integration["Pizza House Service<br/>FastAPI :8001"]
    database[("PostgreSQL<br/>заведения, товары, заказы")]

    user -->|"HTTP/JSON<br/>просмотр меню и заказ"| main
    restaurant -->|"HTTP/JSON<br/>статусы заказа"| integration
    main -->|"проверка цены и остатка"| integration
    integration -->|"обновление статуса"| main
    main -->|"SQLAlchemy"| database
```

Main Service является источником истины для заказов и хранит копию
каталога заведений. Pizza House Service имитирует внешнюю систему
ресторана и хранит актуальные остатки и цены демонстрационного заведения.

## Компоненты Main Service

```mermaid
flowchart TB
    api["FastAPI endpoints<br/>app/main.py"]
    schemas["Pydantic schemas<br/>app/schemas.py"]
    services["Business services<br/>app/services"]
    orm["SQLAlchemy models<br/>app/models.py"]
    migrations["Alembic migrations"]
    postgres[("PostgreSQL")]
    external["Pizza House API"]

    api --> schemas
    api --> services
    services --> orm
    services --> external
    orm --> postgres
    migrations --> postgres
```

## CJM пользователя

```mermaid
sequenceDiagram
    actor User as Пользователь
    participant Web as Web-клиент
    participant Main as Main Service
    participant Cafe as Pizza House
    participant DB as PostgreSQL

    User->>Web: Открывает Авито.Кухню
    Web->>Main: GET /establishments
    Main->>DB: Получить активные заведения
    DB-->>Main: Список заведений
    Main-->>Web: Карточки заведений

    User->>Web: Выбирает заведение
    Web->>Main: GET /establishments/{id}/products
    Main->>DB: Получить доступные товары
    DB-->>Main: Меню
    Main-->>Web: Карточки товаров

    User->>Web: Добавляет товары и оформляет заказ
    Web->>Main: POST /establishments/{id}/orders
    Main->>DB: Проверить локальные цены и доступность
    Main->>Cafe: POST /integration/orders/validate
    Cafe-->>Main: Актуальные цены и остатки

    alt Товар доступен, цена не изменилась
        Main->>DB: Сохранить заказ и снимки цен
        Main-->>Web: 201, заказ в статусе pending
    else Товар закончился или цена изменилась
        Main-->>Web: 409 со списком конфликтов
        Web-->>User: Показать причину и предложить изменить корзину
    end
```

## CJM заведения

```mermaid
sequenceDiagram
    actor Employee as Сотрудник заведения
    participant Cafe as Pizza House
    participant Main as Main Service
    participant DB as PostgreSQL

    Main->>Cafe: Проверить новый заказ
    Cafe->>Cafe: Сверить меню, цену и остаток
    Cafe-->>Main: accepted=true или conflicts

    Employee->>Cafe: Принять заказ
    Cafe->>Main: PATCH /orders/{id}/status = accepted
    Main->>DB: Обновить статус

    Employee->>Cafe: Начать приготовление
    Cafe->>Main: status = preparing
    Main->>DB: Обновить статус

    Employee->>Cafe: Заказ готов
    Cafe->>Main: status = ready
    Main->>DB: Обновить статус

    Main-->>Cafe: Текущее представление заказа
```

## Жизненный цикл заказа

```mermaid
stateDiagram-v2
    [*] --> pending
    pending --> accepted
    pending --> rejected
    pending --> cancelled
    accepted --> preparing
    accepted --> rejected
    accepted --> cancelled
    preparing --> ready
    preparing --> rejected
    ready --> in_delivery
    in_delivery --> delivered
    delivered --> [*]
    rejected --> [*]
    cancelled --> [*]
```

`rejected` устанавливается заведением, а `cancelled` — пользователем.
Для перехода в `rejected` обязательно указывается причина.

## Схема базы данных

```mermaid
erDiagram
    ESTABLISHMENTS ||--o{ PRODUCTS : contains
    ESTABLISHMENTS ||--o{ ORDERS : receives
    ORDERS ||--|{ ORDER_ITEMS : contains
    PRODUCTS ||--o{ ORDER_ITEMS : referenced_by

    ESTABLISHMENTS {
        int id PK
        varchar external_id UK
        varchar name
        varchar establishment_type
        varchar address
        boolean is_active
    }

    PRODUCTS {
        int id PK
        int establishment_id FK
        varchar external_id
        varchar name
        varchar description
        varchar category
        numeric price
        boolean is_available
    }

    ORDERS {
        int id PK
        int establishment_id FK
        varchar customer_name
        varchar customer_phone
        varchar delivery_address
        varchar status
        varchar rejection_reason
        numeric items_total
        numeric delivery_price
        numeric total_price
        timestamptz created_at
        timestamptz updated_at
    }

    ORDER_ITEMS {
        int id PK
        int order_id FK
        int product_id FK
        varchar external_product_id
        varchar product_name
        numeric unit_price
        int quantity
        numeric line_total
    }
```

В `order_items` сохраняется снимок названия и цены. Поэтому уже созданный
заказ не изменится, если ресторан позднее переименует товар или обновит цену.

## Решения и ограничения MVP

- Авторизация отсутствует согласно условиям задания.
- Корзина хранится на стороне клиента; сервер повторно проверяет её при заказе.
- Денежные значения хранятся как `NUMERIC(12, 2)`/`Decimal`, а не `float`.
- Один заказ относится только к одному заведению.
- Сервис заведения хранит меню в памяти для демонстрации интеграции.
- Распределённая транзакция и резервирование остатков не реализованы.
- При недоступности сервиса заведения Main Service отвечает кодом `503`.
- При изменении цены или отсутствии товара возвращается `409` с конфликтами.