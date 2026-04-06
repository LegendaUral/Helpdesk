"""Маршруты авторизации"""
from flask import render_template, request, redirect, url_for, session, flash
from models import db, User


def setup_auth_routes(app):
    """Регистрирует маршруты авторизации"""
    
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
