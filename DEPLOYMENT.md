# Развёртывание и Администрирование HelpDesk

## 🖥️ Системные требования

### Минимальные
- **OS**: Windows, Linux, macOS
- **Python**: 3.8+
- **ОЗУ**: 512 MB
- **Диск**: 100 MB (для приложения + БД)
- **Процессор**: 1+ ядро

### Рекомендуемые
- **Python**: 3.10+
- **ОЗУ**: 2 GB (для < 100 одновременных пользователей)
- **Диск**: 1 GB
- **Процессор**: 2+ ядра

---

## 📦 Установка локально

### Шаг 1: Клонирование/скачивание проекта
```bash
git clone https://github.com/YourUsername/helpdesk.git
cd helpdesk
```

### Шаг 2: Создание виртуального окружения
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Шаг 3: Установка зависимостей
```bash
pip install -r requirements.txt
```

### Шаг 4: Запуск приложения
```bash
python app.py
```

### Шаг 5: Открыть в браузере
```
http://localhost:5000
```

### Шаг 6: Создание администратора
1. На странице `/setup` заполнить данные
2. Нажать **Создать администратора**
3. Готово!

---

## 🌐 Развёртывание на VPS/выделенном сервере

### Вариант 1: Gunicorn + Nginx

#### 1. Подготовка сервера (Ubuntu 20.04+)
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv nginx -y
```

#### 2. Клонирование проекта
```bash
cd /var/www
sudo git clone https://github.com/YourUsername/helpdesk.git
cd helpdesk
sudo chown -R www-data:www-data .
```

#### 3. Создание виртуального окружения
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

#### 4. Тест Gunicorn
```bash
gunicorn --workers 4 --bind 127.0.0.1:8000 app:app
```

#### 5. Создание systemd сервиса
```bash
sudo nano /etc/systemd/system/helpdesk.service
```

Вставить:
```ini
[Unit]
Description=HelpDesk Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/helpdesk
ExecStart=/var/www/helpdesk/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:8000 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Сохранить и выйти (Ctrl+X, Y, Enter).

#### 6. Запуск сервиса
```bash
sudo systemctl daemon-reload
sudo systemctl enable helpdesk
sudo systemctl start helpdesk
sudo systemctl status helpdesk
```

#### 7. Конфигурация Nginx
```bash
sudo nano /etc/nginx/sites-available/helpdesk
```

Вставить:
```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/helpdesk/static/;
    }
}
```

#### 8. Включение конфигурации
```bash
sudo ln -s /etc/nginx/sites-available/helpdesk /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 9. SSL сертификат (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your_domain.com
```

### Вариант 2: Docker

#### Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "app:app"]
```

#### docker-compose.yml
```yaml
version: '3.8'

services:
  helpdesk:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./instance:/app/instance
    environment:
      - FLASK_ENV=production
    restart: always

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - helpdesk
    restart: always
```

#### Запуск с Docker
```bash
docker-compose up -d
```

---

## 🔧 Административные задачи

### Резервное копирование БД

#### Автоматический бэкап (Linux cron)
```bash
# Открыть crontab
crontab -e

# Добавить строку (ежедневно в 02:00)
0 2 * * * cp /var/www/helpdesk/instance/helpdesk.db /var/www/helpdesk/backups/helpdesk_$(date +\%Y\%m\%d).db
```

#### Ручной бэкап
```bash
# Linux/Mac
cp instance/helpdesk.db instance/helpdesk.db.backup

# Windows
copy instance\helpdesk.db instance\helpdesk.db.backup
```

### Восстановление из бэкапа
```bash
# Linux/Mac
cp instance/helpdesk.db.backup instance/helpdesk.db

# Windows
copy instance\helpdesk.db.backup instance\helpdesk.db
```

### Мониторинг логов

#### Systemd лог
```bash
sudo journalctl -u helpdesk -f
```

#### Nginx лог
```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

---

## 📊 Оптимизация производительности

### 1. Увеличение количества рабочих процессов Gunicorn

```bash
# По умолчанию: 4 работника
# Оптимум: (2 * CPU_cores) + 1

gunicorn --workers 9 --bind 0.0.0.0:5000 app:app
```

### 2. Добавление кеша (Redis)

#### Установка Redis
```bash
# Linux
sudo apt install redis-server -y
sudo systemctl start redis-server

# Mac
brew install redis
redis-server
```

#### Использование Redis в Flask
```python
# В app.py
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'redis'})

@app.route('/api/tickets')
@cache.cached(timeout=60)  # Кеш на 60 секунд
def api_tickets():
    ...
```

### 3. Добавление индексов в БД

```python
# В models.py добавить индексы
class Ticket(db.Model):
    ...
    __table_args__ = (
        db.Index('idx_status', 'status'),
        db.Index('idx_author_id', 'author_id'),
        db.Index('idx_executor_id', 'executor_id'),
    )
```

### 4. Ограничение размера логов

```bash
# Linux: настроить rotation
sudo nano /etc/logrotate.d/nginx
```

---

## 🚨 Troubleshooting

### Приложение не запускается

**Проблема**: `ModuleNotFoundError: No module named 'flask'`

**Решение**:
```bash
pip install -r requirements.txt
```

### Порт уже занят

**Проблема**: `Address already in use`

**Решение**:
```bash
# Найти процесс
lsof -i :5000

# Убить процесс (Linux)
kill -9 <PID>

# Или использовать другой порт
python app.py --port 5001
```

### БД повреждена

**Проблема**: `DatabaseError: database disk image is malformed`

**Решение**:
```bash
# Удалить и пересоздать БД
rm instance/helpdesk.db
python app.py
```

### Медленная работа

**Причины**:
1. Мало рабочих процессов
2. Нет индексов в БД
3. Много одновременных пользователей

**Решение**:
- Увеличить `--workers`
- Добавить индексы
- Использовать Redis для кеша

### Статические файлы не загружаются

**Проблема**: Картинки/CSS не работают при развёртывании

**Решение**: Убедиться, что Nginx правильно сконфигурирован

```nginx
location /static/ {
    alias /var/www/helpdesk/static/;
}
```

---

## 🔐 Безопасность при развёртывании

### 1. Изменить SECRET_KEY

```python
# config.py
import os
SECRET_KEY = os.environ.get('SECRET_KEY', 'default-insecure-key')
```

### 2. Использовать переменные окружения

```bash
# .env файл
SECRET_KEY=super-secure-random-key-here
DATABASE_URL=sqlite:///helpdesk.db
FLASK_ENV=production
```

### 3. Включить HTTPS

```bash
# Автоматически через Let's Encrypt
sudo certbot --nginx -d your_domain.com
```

### 4. Настроить CORS (если нужно)

```python
from flask_cors import CORS
CORS(app, resources={r"/api/*": {"origins": "your_domain.com"}})
```

### 5. Защита от брутфорса

```python
# В routes/auth.py добавить
from flask_limiter import Limiter
limiter = Limiter(app)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    ...
```

---

## 📈 Мониторинг здоровья приложения

### Healthcheck endpoint
```python
@app.route('/health')
def health():
    try:
        # Проверить БД
        db.session.execute('SELECT 1')
        return jsonify(status='healthy'), 200
    except:
        return jsonify(status='unhealthy'), 500
```

### Проверка с помощью curl
```bash
curl http://localhost:5000/health
# {"status":"healthy"}
```

---

## 🔄 Обновление приложения

### Обновление кода
```bash
cd /var/www/helpdesk
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart helpdesk
```

### Миграция БД (если нужна)
```bash
# Текущая версия использует auto-migration
# При обновлении моделей просто перезагрузите приложение
python app.py
```

---

## 📞 Техническая поддержка

### Логирование ошибок
```python
# В app.py добавить
import logging
logging.basicConfig(filename='helpdesk.log', level=logging.ERROR)
```

### Отправка логов при ошибках
```python
# При деплое на production:
app.logger.error(f"Error: {str(error)}")
```

### Контакты поддержки
- Email: support@example.com
- GitHub Issues: https://github.com/YourUsername/helpdesk/issues
- Documentation: https://github.com/YourUsername/helpdesk/wiki

---

## 📋 Чеклист перед production

- [ ] Изменена `SECRET_KEY`
- [ ] Установлены переменные окружения
- [ ] Включен HTTPS (SSL)
- [ ] Настроена CORS (если нужна)
- [ ] Созданы резервные копии БД
- [ ] Настроен мониторинг логов
- [ ] Увеличено количество рабочих процессов
- [ ] Добавлены индексы в БД
- [ ] Настроен firewall
- [ ] Протестировано в боевых условиях

---

## 🎓 Дополнительные ресурсы

- [Flask Deployment Options](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Gunicorn Documentation](https://gunicorn.org/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Let's Encrypt](https://letsencrypt.org/)
