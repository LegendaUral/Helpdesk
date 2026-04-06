from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, Response, jsonify
from datetime import datetime, timezone
from config import Config
from models import db, User, Ticket, Message
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from sqlalchemy import or_, case
import os

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
# Благодаря context_processor не нужно передавать их вручную каждый раз
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


# ── Проверка авторизации ──────────────────────────────────────────────
# Вместо одинакового if/redirect в каждой функции — один вызов
def auth_required(role=None):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if role and session['user_role'] not in (role if isinstance(role, list) else [role]):
        flash('Недостаточно прав.', 'danger')
        return redirect(url_for('index'))
    return None  # всё в порядке


# Форматтер дат — конвертирует время в Asia/Yekaterinburg и форматирует строкой
@app.template_filter('format_dt')
def format_dt(value, fmt='%d.%m.%Y %H:%M'):
    if not value:
        return ''
    # Если datetime без tzinfo — считаем, что это UTC
    try:
        tz_target = ZoneInfo('Asia/Yekaterinburg')
    except Exception:
        # fallback to UTC if zoneinfo not available
        tz_target = timezone.utc
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    try:
        local = value.astimezone(tz_target)
    except Exception:
        local = value
    return local.strftime(fmt)


# ── Авторизация ───────────────────────────────────────────────────────

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if User.query.first():
        return redirect(url_for('login'))
    if request.method == 'POST':
        name, email = request.form.get('name','').strip(), request.form.get('email','').strip()
        password, confirm = request.form.get('password',''), request.form.get('confirm','')
        if not name or not email or len(password) < 6 or password != confirm:
            flash('Проверьте заполнение всех полей (пароль мин. 6 символов, пароли должны совпадать).', 'danger')
            return render_template('setup.html', name=name, email=email)
        admin = User(name=name, email=email, role='admin')
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        flash('Администратор создан. Войдите в систему.', 'success')
        return redirect(url_for('login'))
    return render_template('setup.html', name='', email='')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if not User.query.first():
        return redirect(url_for('setup'))
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email','')).first()
        if user and not user.is_deleted and user.check_password(request.form.get('password','')):
            session.update(user_id=user.id, user_role=user.role, user_name=user.name)
            flash(f'Добро пожаловать, {user.name}!', 'success')
            return redirect(url_for('index'))
        flash('Неверный email или пароль.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── Заявки ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    err = auth_required()
    if err: return err
    role, uid = session['user_role'], session['user_id']
    # Сортировка через GET-параметр
    sort = request.args.get('sort', 'created_desc')

    if role == 'admin':
        q = Ticket.query
    elif role == 'support':
        # support видит свои и незназначенные
        q = Ticket.query.filter(or_(Ticket.executor_id == uid, Ticket.executor_id.is_(None)))
    else:
        q = Ticket.query.filter_by(author_id=uid)

    # Применяем сортировку
    if sort == 'created_asc':
        q = q.order_by(Ticket.created_at.asc())
    elif sort == 'priority':
        # high → medium → low
        priority_order = case(
            (Ticket.priority == 'high', 1),
            (Ticket.priority == 'medium', 2),
            (Ticket.priority == 'low', 3),
            else_=4
        )
        q = q.order_by(priority_order, Ticket.created_at.desc())
    elif sort == 'status':
        # new → in_progress → resolved → closed
        status_order = case(
            (Ticket.status == 'new', 1),
            (Ticket.status == 'in_progress', 2),
            (Ticket.status == 'resolved', 3),
            (Ticket.status == 'closed', 4),
            else_=5
        )
        q = q.order_by(status_order, Ticket.created_at.desc())
    else:  # created_desc
        q = q.order_by(Ticket.created_at.desc())

    tickets = q.all()
    return render_template('index.html', tickets=tickets, current_sort=sort)


@app.route('/tickets/new', methods=['GET', 'POST'])
def new_ticket():
    err = auth_required()
    if err: return err
    
    # Специалисты поддержки не могут создавать заявки
    if session['user_role'] == 'support':
        flash('Специалисты поддержки не могут создавать заявки.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title       = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        if not title or not description:
            flash('Заполните все обязательные поля.', 'danger')
            return render_template('new_ticket.html')
        ticket = Ticket(title=title, description=description,
                        priority=request.form.get('priority', 'medium'),
                        author_id=session['user_id'])
        db.session.add(ticket)
        db.session.commit()
        flash(f'Заявка №{ticket.id} успешно создана.', 'success')
        return redirect(url_for('index'))
    return render_template('new_ticket.html')


@app.route('/tickets/<int:ticket_id>')
def ticket_detail(ticket_id):
    err = auth_required()
    if err: return err
    ticket    = Ticket.query.get_or_404(ticket_id)
    executors = User.query.filter_by(role='support', is_deleted=False).order_by(User.name).all()
    return render_template('ticket.html', ticket=ticket, executors=executors)


@app.route('/tickets/<int:ticket_id>/status', methods=['POST'])
def change_status(ticket_id):
    err = auth_required(role=['support', 'admin'])
    if err: return err
    ticket     = Ticket.query.get_or_404(ticket_id)
    new_status = request.form.get('status')
    if new_status in ('new', 'in_progress', 'resolved', 'closed'):
        ticket.status     = new_status
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Статус обновлён.', 'success')
    return redirect(url_for('ticket_detail', ticket_id=ticket_id))


@app.route('/tickets/<int:ticket_id>/assign', methods=['POST'])
def assign_executor(ticket_id):
    err = auth_required(role='admin')
    if err: return err
    ticket = Ticket.query.get_or_404(ticket_id)
    eid    = request.form.get('executor_id')
    ticket.executor_id = int(eid) if eid else None
    ticket.updated_at  = datetime.utcnow()
    db.session.commit()
    flash('Исполнитель назначен.', 'success')
    return redirect(url_for('ticket_detail', ticket_id=ticket_id))


@app.route('/tickets/<int:ticket_id>/take', methods=['POST'])
def take_ticket(ticket_id):
    """Специалист берёт заявку в работу (назначает себя)"""
    err = auth_required(role=['support', 'admin'])
    if err: return err
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Можно взять только если не назначена никому или я уже назначен
    if ticket.executor_id and ticket.executor_id != session['user_id']:
        flash('Заявка уже назначена другому специалисту.', 'warning')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))
    
    ticket.executor_id = session['user_id']
    if ticket.status == 'new':
        ticket.status = 'in_progress'
    ticket.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Вы взяли заявку в работу.', 'success')
    return redirect(url_for('ticket_detail', ticket_id=ticket_id))


@app.route('/tickets/<int:ticket_id>/release', methods=['POST'])
def release_ticket(ticket_id):
    """Специалист отпускает заявку (отменяет своё назначение)"""
    err = auth_required(role=['support', 'admin'])
    if err: return err
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Можно отпустить только если я назначен или я админ
    if ticket.executor_id != session['user_id'] and session['user_role'] != 'admin':
        flash('Вы не являетесь исполнителем.', 'danger')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))
    
    ticket.executor_id = None
    ticket.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Заявка отпущена.', 'success')
    return redirect(url_for('ticket_detail', ticket_id=ticket_id))


# ── Поиск ─────────────────────────────────────────────────────────────

@app.route('/tickets/search')
def search_tickets():
    err = auth_required()
    if err: return err
    name  = request.args.get('executor', '').strip()
    dfrom = request.args.get('date_from', '').strip()
    dto   = request.args.get('date_to',   '').strip()
    sort  = request.args.get('sort', 'created_desc')
    q     = Ticket.query
    # Ограничение видимости по роли — support видит свои и незназначенные
    role, uid = session['user_role'], session['user_id']
    if role == 'support':
        q = q.filter(or_(Ticket.executor_id == uid, Ticket.executor_id.is_(None)))
    elif role == 'user':
        q = q.filter_by(author_id=uid)
    if name:
        q = q.join(User, Ticket.executor_id == User.id)\
             .filter(User.name.ilike(f'%{name}%'))
    if dfrom:
        try:    q = q.filter(Ticket.created_at >= datetime.strptime(dfrom, '%Y-%m-%d'))
        except: flash('Неверный формат даты.', 'warning')
    if dto:
        try:
            q = q.filter(Ticket.created_at <=
                         datetime.strptime(dto, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        except: flash('Неверный формат даты.', 'warning')
    
    # Применяем сортировку один раз (правильно!)
    if sort == 'created_asc':
        q = q.order_by(Ticket.created_at.asc())
    elif sort == 'priority':
        # high → medium → low
        from sqlalchemy import case
        priority_order = case(
            (Ticket.priority == 'high', 1),
            (Ticket.priority == 'medium', 2),
            (Ticket.priority == 'low', 3),
            else_=4
        )
        q = q.order_by(priority_order, Ticket.created_at.desc())
    elif sort == 'status':
        # new → in_progress → resolved → closed
        status_order = case(
            (Ticket.status == 'new', 1),
            (Ticket.status == 'in_progress', 2),
            (Ticket.status == 'resolved', 3),
            (Ticket.status == 'closed', 4),
            else_=5
        )
        q = q.order_by(status_order, Ticket.created_at.desc())
    else:  # created_desc
        q = q.order_by(Ticket.created_at.desc())
    
    tickets = q.all()
    executors = User.query.filter_by(role='support', is_deleted=False).order_by(User.name).all()

    return render_template('search.html', tickets=tickets, executors=executors,
                           executor_name=name, date_from=dfrom, date_to=dto, current_sort=sort)


# ── Пользователи (только admin) ───────────────────────────────────────

@app.route('/users')
def users_list():
    err = auth_required(role='admin')
    if err: return err
    return render_template('users.html', users=User.query.filter_by(is_deleted=False).order_by(User.name).all())


@app.route('/users/deleted')
def deleted_users_list():
    err = auth_required(role='admin')
    if err: return err
    return render_template('deleted_users.html', users=User.query.filter_by(is_deleted=True).order_by(User.name).all())


@app.route('/users/new', methods=['GET', 'POST'])
def new_user():
    err = auth_required(role='admin')
    if err: return err
    if request.method == 'POST':
        name, email = request.form.get('name','').strip(), request.form.get('email','').strip()
        password    = request.form.get('password', '')
        role        = request.form.get('role', 'user')
        if not name or not email or not password:
            flash('Заполните все поля.', 'danger')
            return render_template('new_user.html')
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует.', 'danger')
            return render_template('new_user.html')
        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f'Пользователь {name} создан.', 'success')
        return redirect(url_for('users_list'))
    return render_template('new_user.html')


@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    err = auth_required(role='admin')
    if err: return err
    user = User.query.get_or_404(user_id)
    
    # Защита: нельзя изменить роль первого администратора (ID=1)
    if user.id == 1:
        flash('Невозможно редактировать первого администратора системы.', 'danger')
        return redirect(url_for('users_list'))
    
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        role = request.form.get('role', 'user')
        password = request.form.get('password', '').strip()
        
        if not name or not email:
            flash('Заполните имя и email.', 'danger')
            return render_template('edit_user.html', user=user)
        
        # Проверка email на уникальность (кроме текущего пользователя)
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != user.id:
            flash('Пользователь с таким email уже существует.', 'danger')
            return render_template('edit_user.html', user=user)
        
        user.name = name
        user.email = email
        user.role = role
        if password:  # Обновляем пароль только если заполнено новое значение
            user.set_password(password)
        db.session.commit()
        flash(f'Пользователь {name} обновлён.', 'success')
        return redirect(url_for('users_list'))
    
    return render_template('edit_user.html', user=user)


@app.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    err = auth_required(role='admin')
    if err: return err
    user = User.query.get_or_404(user_id)
    
    # Защита: нельзя удалить первого администратора (ID=1)
    if user.id == 1:
        flash('Невозможно удалить первого администратора системы.', 'danger')
        return redirect(url_for('users_list'))
    
    # Защита от удаления единственного админа
    if user.role == 'admin' and User.query.filter_by(role='admin', is_deleted=False).count() <= 1:
        flash('Невозможно удалить последнего администратора.', 'danger')
        return redirect(url_for('users_list'))
    
    # Маркируем пользователя как удалённого
    user.is_deleted = True
    
    # Закрываем все открытые заявки, где он автор
    Ticket.query.filter_by(author_id=user.id).filter(
        Ticket.status.in_(['new', 'in_progress'])
    ).update({'status': 'closed', 'updated_at': datetime.utcnow()})
    
    # Удаляем его из должности исполнителя во всех заявках
    Ticket.query.filter_by(executor_id=user.id).update({'executor_id': None})
    
    name = user.name
    db.session.commit()
    flash(f'Пользователь {name} удалён. Его открытые заявки закрыты, исполнитель в остальных — обнулен.', 'success')
    return redirect(url_for('users_list'))


# ── Чат в заявках ─────────────────────────────────────────────────

@app.route('/tickets/<int:ticket_id>/message', methods=['POST'])
def add_message(ticket_id):
    err = auth_required()
    if err: return err
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Проверка прав: только автор, исполнитель или админ могут писать
    user_id = session['user_id']
    if user_id not in (ticket.author_id, ticket.executor_id) and session['user_role'] != 'admin':
        flash('У вас нет прав на эту заявку.', 'danger')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))
    
    text = request.form.get('text', '').strip()
    if not text:
        flash('Сообщение не может быть пусто.', 'danger')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))
    
    msg = Message(ticket_id=ticket_id, user_id=user_id, text=text)
    db.session.add(msg)
    db.session.commit()
    
    return redirect(url_for('ticket_detail', ticket_id=ticket_id))


@app.route('/api/messages/<int:ticket_id>')
def api_messages(ticket_id):
    """Возвращает все сообщения заявки в JSON"""
    err = auth_required()
    if err: return err
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Проверка прав: только автор, исполнитель или админ могут видеть чат
    user_id = session['user_id']
    if user_id not in (ticket.author_id, ticket.executor_id) and session['user_role'] != 'admin':
        return jsonify([]), 403
    
    messages = ticket.messages
    
    msgs_data = []
    for m in messages:
        msgs_data.append({
            'id': m.id,
            'user_name': m.user.name,
            'user_role': m.user.role,
            'text': m.text,
            'created_at': m.created_at.isoformat()
        })
    
    return jsonify(msgs_data)


# ── API для автообновления заявок ─────────────────────────────────

@app.route('/api/tickets')
def api_tickets():
    """Возвращает список заявок в JSON для автообновления"""
    err = auth_required()
    if err: return err
    
    from flask import jsonify
    role, uid = session['user_role'], session['user_id']
    sort = request.args.get('sort', 'created_desc')
    
    if role == 'admin':
        q = Ticket.query
    elif role == 'support':
        q = Ticket.query.filter(or_(Ticket.executor_id == uid, Ticket.executor_id.is_(None)))
    else:
        q = Ticket.query.filter_by(author_id=uid)
    
    # Применяем сортировку
    if sort == 'created_asc':
        q = q.order_by(Ticket.created_at.asc())
    elif sort == 'priority':
        priority_order = case(
            (Ticket.priority == 'high', 1),
            (Ticket.priority == 'medium', 2),
            (Ticket.priority == 'low', 3),
            else_=4
        )
        q = q.order_by(priority_order, Ticket.created_at.desc())
    elif sort == 'status':
        status_order = case(
            (Ticket.status == 'new', 1),
            (Ticket.status == 'in_progress', 2),
            (Ticket.status == 'resolved', 3),
            (Ticket.status == 'closed', 4),
            else_=5
        )
        q = q.order_by(status_order, Ticket.created_at.desc())
    else:
        q = q.order_by(Ticket.created_at.desc())
    
    tickets = q.all()
    
    # Форматируем для JSON
    tickets_data = []
    for t in tickets:
        tickets_data.append({
            'id': t.id,
            'title': t.title,
            'priority': t.priority,
            'status': t.status,
            'created_at': t.created_at.isoformat(),
            'executor_name': t.executor.name if t.executor else 'Не назначен'
        })
    
    return jsonify(tickets_data)
# ── Service Worker ────────────────────────────────────────────────────

@app.route('/service-worker.js')
def service_worker():
    sw_path = os.path.join(os.path.dirname(__file__), 'static', 'service-worker.js')
    with open(sw_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return Response(content, mimetype='application/javascript')


# ── Запуск ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.first():
            print('База пустая. Откройте http://localhost:5000 для настройки.')
    app.run(debug=True, host='0.0.0.0', port=5000)
