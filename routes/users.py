"""Маршруты управления пользователями"""
from flask import render_template, request, redirect, url_for, session, flash
from datetime import datetime
from models import db, User, Ticket


def setup_users_routes(app, auth_required):
    """Регистрирует маршруты пользователей"""
    
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
            
            existing = User.query.filter_by(email=email).first()
            if existing and existing.id != user.id:
                flash('Пользователь с таким email уже существует.', 'danger')
                return render_template('edit_user.html', user=user)
            
            user.name = name
            user.email = email
            user.role = role
            if password:
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
        
        if user.id == 1:
            flash('Невозможно удалить первого администратора системы.', 'danger')
            return redirect(url_for('users_list'))
        
        if user.role == 'admin' and User.query.filter_by(role='admin', is_deleted=False).count() <= 1:
            flash('Невозможно удалить последнего администратора.', 'danger')
            return redirect(url_for('users_list'))
        
        user.is_deleted = True
        
        Ticket.query.filter_by(author_id=user.id).filter(
            Ticket.status.in_(['new', 'in_progress'])
        ).update({'status': 'closed', 'updated_at': datetime.utcnow()})
        
        Ticket.query.filter_by(executor_id=user.id).update({'executor_id': None})
        
        name = user.name
        db.session.commit()
        flash(f'Пользователь {name} удалён. Его открытые заявки закрыты, исполнитель в остальных — обнулен.', 'success')
        return redirect(url_for('users_list'))
