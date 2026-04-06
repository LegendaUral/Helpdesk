from flask import Flask, redirect, url_for, session, flash
from datetime import datetime, timezone
from config import Config
from models import db, User
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
import os

# Импортируем утилиты и роуты
from utils import auth_required
from routes import register_routes

# ── Создание приложения и конфигурация ────────────────────────────────

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)


# ── Проверка удалённого пользователя перед каждым запросом ───────────
@app.before_request
def check_deleted_user():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if not user or user.is_deleted:
            session.clear()
            flash('Ваша учётная запись была удалена.', 'warning')
            return redirect(url_for('login'))


# ── Словари автоматически доступны во всех шаблонах ──────────────────
@app.context_processor
def inject_dicts():
    return dict(
        priority_labels = {'low': 'Низкий',  'medium': 'Средний', 'high': 'Высокий'},
        priority_colors = {'low': 'success', 'medium': 'warning',  'high': 'danger'},
        status_labels   = {'new': 'Новая', 'in_progress': 'В работе',
                           'resolved': 'Решена', 'closed': 'Закрыта'},
        status_colors   = {'new': 'primary', 'in_progress': 'warning',
                           'resolved': 'success', 'closed': 'secondary'},
        role_labels     = {'user': 'Сотрудник', 'support': 'Специалист', 'admin': 'Администратор'},
    )


# ── Форматтер дат для шаблонов ─────────────────────────────────────────
@app.template_filter('format_dt')
def format_dt(value, fmt='%d.%m.%Y %H:%M'):
    if not value:
        return ''
    try:
        tz_target = ZoneInfo('Asia/Yekaterinburg')
    except Exception:
        tz_target = timezone.utc
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    try:
        local = value.astimezone(tz_target)
    except Exception:
        local = value
    return local.strftime(fmt)


# ── Регистрация всех маршрутов ─────────────────────────────────────────
register_routes(app, auth_required)


# ── Запуск ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.first():
            print('База пустая. Откройте http://localhost:5000 для настройки.')
    app.run(debug=True, host='0.0.0.0', port=5000)
