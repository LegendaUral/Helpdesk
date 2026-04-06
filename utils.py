"""Утилиты приложения"""
from flask import redirect, url_for, session, flash


def auth_required(role=None):
    """Проверка авторизации и прав доступа"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if role and session['user_role'] not in (role if isinstance(role, list) else [role]):
        flash('Недостаточно прав.', 'danger')
        return redirect(url_for('index'))
    return None
