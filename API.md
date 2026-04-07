# API Документация HelpDesk

## 📡 Введение

HelpDesk предоставляет REST API для программного доступа к заявкам и сообщениям. API использует JSON для передачи данных и требует аутентификации через сессии Flask.

---

## 🔐 Аутентификация

### Сессия
Все запросы к API требуют активной сессии пользователя.

**Получение сессии:**
```bash
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=user@example.com&password=password" \
  -c cookies.txt
```

**Использование сессии в запросах:**
```bash
curl -X GET http://localhost:5000/api/tickets \
  -b cookies.txt
```

### Ошибки аутентификации
```json
{
  "error": "Unauthorized",
  "status": 401
}
```

---

## 📊 Endpoints

### GET /api/messages/<ticket_id>

Получить все сообщения для заявки в формате JSON.

#### Параметры
- `ticket_id` (int, обязательный) — ID заявки

#### Ответ 200 OK
```json
[
  {
    "id": 1,
    "user_name": "Иван Иванов",
    "user_role": "support",
    "text": "Спасибо за сообщение. Работаю над проблемой.",
    "created_at": "2024-01-15T10:30:45"
  },
  {
    "id": 2,
    "user_name": "Петр Петров",
    "user_role": "user",
    "text": "Спасибо! Ждём новостей.",
    "created_at": "2024-01-15T11:15:20"
  }
]
```

#### Ошибки
- **404 Not Found** — заявка не существует
- **403 Forbidden** — нет прав доступа к заявке
- **401 Unauthorized** — не авторизирован

#### Пример использования
```bash
curl -X GET http://localhost:5000/api/messages/1 \
  -b cookies.txt
```

---

### GET /api/tickets

Получить список заявок в формате JSON с фильтрацией по ролям.

#### Параметры query
- `sort` (string, optional) — метод сортировки
  - `created_desc` (default) — по дате создания (новые сначала)
  - `created_asc` — по дате создания (старые сначала)
  - `priority` — по приоритету (высокий сначала)
  - `status` — по статусу (новые сначала)

#### Ответ 200 OK
```json
{
  "tickets": [
    {
      "id": 1,
      "title": "Не открывается веб-сайт",
      "description": "При открытии сайта компании...",
      "priority": "high",
      "status": "in_progress",
      "author": {
        "id": 2,
        "name": "Иван Иванов"
      },
      "executor": {
        "id": 3,
        "name": "Петр Петров"
      },
      "created_at": "2024-01-15T08:00:00",
      "updated_at": "2024-01-15T10:30:00"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 50
}
```

#### Поведение по ролям
- **user** — видит только свои заявки
- **support** — видит свои + неназначенные заявки
- **admin** — видит все заявки

#### Примеры
```bash
# Все заявки (по умолчанию)
curl -X GET http://localhost:5000/api/tickets \
  -b cookies.txt

# Отсортированные по приоритету
curl -X GET 'http://localhost:5000/api/tickets?sort=priority' \
  -b cookies.txt

# Отсортированные по статусу
curl -X GET 'http://localhost:5000/api/tickets?sort=status' \
  -b cookies.txt
```

---

## 📮 Постоянно используемые поля

### User объект
```json
{
  "id": 1,
  "name": "Иван Иванов",
  "email": "ivan@example.com",
  "role": "user",
  "created_at": "2024-01-01T12:00:00",
  "is_deleted": false
}
```

### Ticket объект
```json
{
  "id": 1,
  "title": "Заголовок заявки",
  "description": "Полное описание проблемы...",
  "priority": "medium",
  "status": "new",
  "author_id": 2,
  "executor_id": 3,
  "created_at": "2024-01-15T08:00:00",
  "updated_at": "2024-01-15T10:30:00",
  "author": {
    "id": 2,
    "name": "Иван Иванов"
  },
  "executor": {
    "id": 3,
    "name": "Петр Петров"
  }
}
```

### Message объект
```json
{
  "id": 1,
  "ticket_id": 1,
  "user_id": 2,
  "text": "Текст сообщения...",
  "created_at": "2024-01-15T10:30:45",
  "user": {
    "id": 2,
    "name": "Иван Иванов",
    "role": "support"
  }
}
```

---

## 🎯 Примеры работы с API

### Python

```python
import requests
import json

BASE_URL = 'http://localhost:5000'
session = requests.Session()

# Аутентификация
login_data = {
    'email': 'admin@example.com',
    'password': 'password'
}
session.post(f'{BASE_URL}/login', data=login_data)

# Получить все заявки
response = session.get(f'{BASE_URL}/api/tickets')
tickets = response.json()
print(json.dumps(tickets, indent=2, ensure_ascii=False))

# Получить сообщения заявки #1
response = session.get(f'{BASE_URL}/api/messages/1')
messages = response.json()
for msg in messages:
    print(f"{msg['user_name']}: {msg['text']}")
```

### JavaScript (Fetch API)

```javascript
const BASE_URL = 'http://localhost:5000';

// Аутентификация
async function login(email, password) {
  const formData = new FormData();
  formData.append('email', email);
  formData.append('password', password);
  
  const response = await fetch(`${BASE_URL}/login`, {
    method: 'POST',
    body: formData,
    credentials: 'include'
  });
  return response.ok;
}

// Получить все заявки
async function getTickets(sort = 'created_desc') {
  const response = await fetch(
    `${BASE_URL}/api/tickets?sort=${sort}`,
    { credentials: 'include' }
  );
  return response.json();
}

// Получить сообщения
async function getMessages(ticketId) {
  const response = await fetch(
    `${BASE_URL}/api/messages/${ticketId}`,
    { credentials: 'include' }
  );
  return response.json();
}

// Использование
(async () => {
  await login('admin@example.com', 'password');
  const tickets = await getTickets();
  console.log(tickets);
})();
```

### cURL

```bash
# Сохраняем cookies
curl -X POST http://localhost:5000/login \
  -d "email=admin@example.com&password=password" \
  -c cookies.txt

# Получаем все заявки
curl -X GET 'http://localhost:5000/api/tickets?sort=priority' \
  -b cookies.txt \
  -H "Accept: application/json" | jq .

# Получаем сообщения заявки #1
curl -X GET 'http://localhost:5000/api/messages/1' \
  -b cookies.txt \
  -H "Accept: application/json" | jq .
```

---

## 🔄 Жизненный цикл через API

### Сценарий: Обработка заявки специалистом

```python
import requests
import time

BASE_URL = 'http://localhost:5000'
session = requests.Session()

# 1. Вход
login_data = {'email': 'support@example.com', 'password': 'password'}
session.post(f'{BASE_URL}/login', data=login_data)

# 2. Получить список открытых заявок
response = session.get(f'{BASE_URL}/api/tickets?sort=created_desc')
tickets = response.json()['tickets']
ticket = tickets[0]

# 3. Взять заявку в работу
take_response = session.post(
    f'{BASE_URL}/tickets/{ticket["id"]}/take'
)

# 4. Получить все сообщения
messages_response = session.get(f'{BASE_URL}/api/messages/{ticket["id"]}')
messages = messages_response.json()
print(f"Всего сообщений: {len(messages)}")

# 5. Добавить комментарий (через форму)
message_data = {'text': 'Работаю над проблемой'}
session.post(
    f'{BASE_URL}/tickets/{ticket["id"]}/message',
    data=message_data
)

# 6. Дождаться решения...
time.sleep(5)

# 7. Изменить статус на "Решена"
status_data = {'status': 'resolved'}
session.post(
    f'{BASE_URL}/tickets/{ticket["id"]}/status',
    data=status_data
)

# 8. Закрыть заявку
status_data = {'status': 'closed'}
session.post(
    f'{BASE_URL}/tickets/{ticket["id"]}/status',
    data=status_data
)

print("Заявка закрыта")
```

---

## ⚠️ Коды ответов и ошибки

| Код | Значение | Описание |
|-----|----------|---------|
| 200 | OK | Запрос выполнен успешно |
| 302 | Found | Редирект (обычно на /login) |
| 400 | Bad Request | Некорректные данные |
| 401 | Unauthorized | Требуется аутентификация |
| 403 | Forbidden | Недостаточно прав |
| 404 | Not Found | Ресурс не найден |
| 500 | Internal Server Error | Ошибка сервера |

### Пример ошибки
```json
{
  "error": "Ticket not found",
  "status": 404
}
```

---

## 🔍 Полезные советы

### 1. Все запросы требуют сессии
```python
# ❌ Неправильно (без сессии)
import requests
requests.get('http://localhost:5000/api/tickets')
# → 401 Unauthorized (редирект на /login)

# ✅ Правильно (с сессией)
session = requests.Session()
session.post('http://localhost:5000/login', data={...})
session.get('http://localhost:5000/api/tickets')
# → 200 OK
```

### 2. Сортировка по статусу полезна для аналитики
```bash
# Получить список закрытых заявок
curl -X GET 'http://localhost:5000/api/tickets?sort=status' \
  -b cookies.txt | jq '.tickets[] | select(.status == "closed")'
```

### 3. Регулярный опрос сообщений (polling)
```javascript
// Опрашиваем сообщения каждые 3 секунды
setInterval(async () => {
  const messages = await getMessages(1);
  console.log(`Всего сообщений: ${messages.length}`);
}, 3000);
```

### 4. Проверка прав доступа
```python
# При попытке доступа к чужой заявке
response = session.get(f'{BASE_URL}/api/messages/999')
if response.status_code == 403:
    print("У вас нет прав доступа к этой заявке")
```

---

## 🚀 Планы развития API

- [ ] Pagination (постраничная выдача результатов)
- [ ] WebSocket для реал-тайм обновления сообщений
- [ ] Фильтры для API (по статусу, приоритету, дате)
- [ ] Экспорт заявок в CSV/JSON
- [ ] API для создания заявок (POST /api/tickets)
- [ ] Аутентификация через токены (JWT)
- [ ] Rate limiting

---

## 📚 Дополнительные ресурсы

- [REST API Best Practices](https://restfulapi.net/)
- [HTTP Status Codes](https://httpwg.org/specs/rfc7231.html#status.codes)
- [JSON Format](https://www.json.org/)
- [Requests Library (Python)](https://requests.readthedocs.io/)
