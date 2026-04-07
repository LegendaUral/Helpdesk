# Архитектура проекта HelpDesk

## 📐 Общая архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Browser)                       │
│              HTML5 + Bootstrap 5 + JavaScript               │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/JSON
┌────────────────────────▼────────────────────────────────────┐
│              Flask Web Application (app.py)                │
├─────────────────────────────────────────────────────────────┤
│  • Сессии и аутентификация                                 │
│  • Маршруты (Routes)                                        │
│  • Шаблоны (Templates)                                      │
│  • API endpoints                                            │
└────────────────────────┬────────────────────────────────────┘
                         │ ORM
┌────────────────────────▼────────────────────────────────────┐
│         SQLAlchemy ORM + Models (models.py)                 │
├─────────────────────────────────────────────────────────────┤
│  • User                                                     │
│  • Ticket                                                   │
│  • Message                                                  │
└────────────────────────┬────────────────────────────────────┘
                         │ SQL
┌────────────────────────▼────────────────────────────────────┐
│            SQLite Database (helpdesk.db)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Структура каталогов

### Корневой уровень
```
helpdesk/
├── app.py              ← Entry point приложения
├── config.py           ← Конфигурация Flask
├── models.py           ← ORM модели (User, Ticket, Message)
├── utils.py            ← Вспомогательные функции
├── requirements.txt    ← Зависимости
├── README.md           ← Основная документация
└── ARCHITECTURE.md     ← Этот файл
```

### Каталог `routes/`
```
routes/
├── __init__.py         ← Регистрирует все маршруты
├── auth.py             ← /setup, /login, /logout
├── tickets.py          ← /, /tickets/new, /tickets/<id>
├── users.py            ← /users, /users/new, /users/<id>/edit
├── search.py           ← /tickets/search
└── api.py              ← /api/messages/<id>, /api/tickets
```

### Каталог `templates/`
```
templates/
├── base.html           ← Базовый шаблон
├── login.html          ← Форма входа
├── setup.html          ← Первоначальная настройка
├── index.html          ← Список заявок
├── new_ticket.html     ← Форма создания заявки
├── ticket.html         ← Просмотр + чат
├── new_user.html       ← Создание пользователя (admin)
├── edit_user.html      ← Редактирование пользователя (admin)
├── users.html          ← Список пользователей (admin)
├── deleted_users.html  ← Удалённые пользователи (admin)
└── search.html         ← Поиск заявок
```

### Каталог `static/`
```
static/
├── manifest.json       ← PWA манифест
├── service-worker.js   ← Service Worker
├── icon-192.png        ← Иконка PWA
└── icon-512.png        ← Иконка PWA
```

---

## 🔌 Потоки данных

### 1. Аутентификация (auth.py)

```
User        Browser               Flask               Database
 │             │                    │                     │
 │ Вход (POST /login)               │                     │
 │──────────────────────────────────>│                     │
 │             │                    │                     │
 │             │         Проверка пароля                 │
 │             │<───────────────────┤──────────────────────>
 │             │                    │                     │
 │             │         Сессия + cookies                │
 │             │<───────────────────┤                     │
 │             │                    │                     │
 │ Редирект на /                    │                     │
 │<───────────────────────────────────                    │
```

### 2. Создание заявки (tickets.py)

```
User          Browser              Flask              Database
 │              │                   │                    │
 │ GET /tickets/new                 │                    │
 │─────────────────────────────────>│                    │
 │              │                   │                    │
 │              │ HTML форма        │                    │
 │<─────────────────────────────────│                    │
 │              │                   │                    │
 │ POST new_ticket                  │                    │
 │─────────────────────────────────>│                    │
 │              │                   │                    │
 │              │        INSERT Ticket                   │
 │              │────────────────────────────────────────>│
 │              │                   │                    │
 │              │        Ticket created                  │
 │              │<────────────────────────────────────────│
 │              │                   │                    │
 │ Редирект     │                   │                    │
 │<─────────────────────────────────│                    │
```

### 3. Чат в заявке (api.py + ticket.html)

```
Browser                              Flask              Database
  │                                   │                    │
  │ DOMContentLoaded                  │                    │
  │──┐                                │                    │
  │  │ GET /api/messages/<id>         │                    │
  │  │─────────────────────────────────>│                    │
  │  │                                │ SELECT messages    │
  │  │                                │──────────────────────>
  │  │                                │<────────────────────│
  │  │                                │                    │
  │  │ JSON с сообщениями             │                    │
  │  │<─────────────────────────────────│                    │
  │  │                                │                    │
  │  │ Отобразить в UI                │                    │
  │  └──────────────────────────────────┐                  │
  │                                      │                  │
  │ Каждые 3 секунды повторяет запрос  │                  │
  │ (опрос каждые 3000ms)               │                  │
```

---

## 🔐 Система контроля доступа

### Проверка авторизации (`auth_required()` в utils.py)

```python
def auth_required(role=None):
    # 1. Проверка: есть ли user_id в сессии?
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 2. Если требуется роль - проверяем её
    if role and session['user_role'] not in (role if isinstance(role, list) else [role]):
        flash('Недостаточно прав.', 'danger')
        return redirect(url_for('index'))
    
    return None  # Доступ разрешён
```

### Таблица прав доступа

| Маршрут | Роль | user | support | admin |
|---------|------|------|---------|-------|
| `/` | любая | ✅ | ✅ | ✅ |
| `/tickets/new` | not support | ✅ | ❌ | ✅ |
| `/tickets/<id>` | автор/исполнитель | ✅* | ✅* | ✅ |
| `/users` | admin | ❌ | ❌ | ✅ |
| `/users/new` | admin | ❌ | ❌ | ✅ |
| `/users/<id>/edit` | admin | ❌ | ❌ | ✅ |
| `/tickets/<id>/status` | support/admin | ❌ | ✅ | ✅ |

*Автор видит свои заявки, исполнитель — назначенные

---

## 📊 Модели данных

### User (Пользователь)

```python
class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), default='user')
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted    = db.Column(db.Boolean, default=False)
```

**Отношения:**
- `created_tickets` → Tickets (заявки, созданные пользователем)
- `assigned_tickets` → Tickets (заявки, назначенные пользователю)
- `messages` → Messages (сообщения, написанные пользователем)

### Ticket (Заявка)

```python
class Ticket(db.Model):
    __tablename__ = 'tickets'
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority    = db.Column(db.String(20), default='medium')
    status      = db.Column(db.String(20), default='new')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow)
    author_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    executor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    author   = db.relationship('User', foreign_keys=[author_id], backref='created_tickets')
    executor = db.relationship('User', foreign_keys=[executor_id], backref='assigned_tickets')
    messages = db.relationship('Message', backref='ticket', lazy=True, cascade='all, delete-orphan')
```

**Статусы:**
- `new` (Новая) → `in_progress` (В работе) → `resolved` (Решена) → `closed` (Закрыта)

**Приоритеты:**
- `low` (Низкий)
- `medium` (Средний)
- `high` (Высокий)

### Message (Сообщение)

```python
class Message(db.Model):
    __tablename__ = 'messages'
    id         = db.Column(db.Integer, primary_key=True)
    ticket_id  = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    text       = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='messages')
```

---

## 🛣️ Маршруты приложения

### Аутентификация (routes/auth.py)

| Метод | Маршрут | Описание | Требует роль |
|-------|---------|---------|--------------|
| GET | `/setup` | Форма создания админа | - |
| POST | `/setup` | Сохранить админа | - |
| GET | `/login` | Форма входа | - |
| POST | `/login` | Проверить учётные данные | - |
| GET | `/logout` | Выход из системы | любая |

### Заявки (routes/tickets.py)

| Метод | Маршрут | Описание | Требует роль |
|-------|---------|---------|--------------|
| GET | `/` | Список заявок | любая |
| GET | `/tickets/new` | Форма создания | !support |
| POST | `/tickets/new` | Сохранить заявку | !support |
| GET | `/tickets/<id>` | Просмотр + чат | автор/исполнитель/admin |
| POST | `/tickets/<id>/message` | Добавить сообщение | - |
| POST | `/tickets/<id>/status` | Изменить статус | support/admin |
| POST | `/tickets/<id>/executor` | Назначить исполнителя | admin |
| POST | `/tickets/<id>/take` | Взять в работу | support |
| POST | `/tickets/<id>/release` | Отпустить | support |

### Пользователи (routes/users.py)

| Метод | Маршрут | Описание | Требует роль |
|-------|---------|---------|--------------|
| GET | `/users` | Список пользователей | admin |
| GET | `/users/deleted` | Удалённые пользователи | admin |
| GET | `/users/new` | Форма создания | admin |
| POST | `/users/new` | Сохранить пользователя | admin |
| GET | `/users/<id>/edit` | Форма редактирования | admin |
| POST | `/users/<id>/edit` | Сохранить изменения | admin |
| POST | `/users/<id>/delete` | Удалить пользователя | admin |

### Поиск (routes/search.py)

| Метод | Маршрут | Описание | Требует роль |
|-------|---------|---------|--------------|
| GET | `/tickets/search` | Поиск по исполнителю и датам | любая |

### API (routes/api.py)

| Метод | Маршрут | Описание | Требует роль |
|-------|---------|---------|--------------|
| GET | `/api/messages/<ticket_id>` | JSON с сообщениями | - |
| GET | `/api/tickets` | JSON со списком заявок | - |

---

## 🎯 Состояния заявки

```
         ┌─────────┐
         │   NEW   │ (Новая)
         └────┬────┘
              │
              ▼
      ┌──────────────────┐
      │   IN_PROGRESS    │ (В работе)
      └────┬───────┬─────┘
           │       │
           ▼       ▼
       ┌─────┐  ┌──────┐
       │CLOSE│  │SOLVED│ (Решена)
       └─────┘  └──┬───┘
                   │
                   ▼
               ┌──────┐
               │CLOSE │ (Закрыта)
               └──────┘
```

---

## 🔄 Жизненный цикл заявки

1. **Создание** (user)
   - Статус: **NEW**
   - Автор: user
   - Исполнитель: NULL

2. **Назначение** (admin)
   - Назначить специалиста
   - Исполнитель: support

3. **Взятие в работу** (support)
   - Статус: **IN_PROGRESS**
   - Исполнитель: support

4. **Работа** (support)
   - Переписка в чате
   - Может отпустить и вернуть статус на NEW

5. **Решение** (support)
   - Статус: **RESOLVED**

6. **Закрытие** (support или admin)
   - Статус: **CLOSED**
   - Чат становится неактивным

---

## 🔒 Безопасность

### Хеширование паролей
```python
def set_password(self, password):
    self.password_hash = hashlib.sha256(password.encode()).hexdigest()

def check_password(self, password):
    return self.password_hash == hashlib.sha256(password.encode()).hexdigest()
```

### Сессии
- Хранятся на сервере в памяти (Flask)
- Содержат: `user_id`, `user_role`, `user_name`
- Проверяются перед каждым запросом

### Мягкое удаление пользователей
- При удалении пользователя флаг `is_deleted = True`
- Заявки остаются в БД (для истории)
- Если удалён автор: его открытые заявки закрываются
- Если удалён исполнитель: заявки передаются в очередь

---

## 🚀 Как запускается приложение

```python
# app.py главный файл
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создаёт таблицы если их нет
        if not User.query.first():
            print('База пустая. Откройте http://localhost:5000 для настройки.')
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### Порядок запуска:
1. Импорт зависимостей (Flask, SQLAlchemy, etc)
2. Инициализация Flask приложения
3. Загрузка конфигурации из `config.py`
4. Инициализация SQLAlchemy
5. Регистрация всех маршрутов из папки `routes/`
6. Проверка БД (создание таблиц если нужно)
7. Запуск сервера на `0.0.0.0:5000`

---

## 📱 PWA архитектура

### manifest.json
```json
{
  "name": "HelpDesk",
  "short_name": "HelpDesk",
  "icons": [...],
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#0d6efd"
}
```

### Service Worker (service-worker.js)
- Кеширует статические файлы
- Позволяет работать в оффлайне (частично)
- Обновляет кеш при запросах

### Установка на мобильном:
```
Browser → manifest.json → Предложение "Установить" → Иконка на рабочем столе
```

---

## 🧪 Тестирование архитектуры

### Проверка аутентификации
```bash
curl -X POST http://localhost:5000/login \
  -d "email=admin@test.com&password=password" \
  --cookie-jar cookies.txt
```

### Проверка API
```bash
curl -X GET http://localhost:5000/api/tickets \
  --cookie cookies.txt
```

---

## ⚡ Производительность

### Возможные оптимизации:
1. **Кеширование**: Redis для кеша сессий
2. **Пагинация**: Для больших списков заявок
3. **Индексы**: На поля `status`, `executor_id`, `author_id`
4. **Асинхронность**: Celery для фоновых задач

### Текущие ограничения:
- SQLite хорошо для < 10,000 заявок
- Все запросы синхронные
- Нет кеширования (каждый запрос идёт в БД)

---

## 📚 Дополнительные ресурсы

- [Flask документация](https://flask.palletsprojects.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Bootstrap 5](https://getbootstrap.com/)
- [PWA Guide](https://web.dev/progressive-web-apps/)
