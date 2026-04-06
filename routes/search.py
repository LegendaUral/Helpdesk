"""Маршруты поиска и фильтрации"""
from flask import render_template, request, flash, redirect, url_for, session
from datetime import datetime
from sqlalchemy import or_, case
from models import db, User, Ticket


def setup_search_routes(app, auth_required):
    """Регистрирует маршруты поиска"""
    
    @app.route('/tickets/search')
    def search_tickets():
        err = auth_required()
        if err: return err
        name  = request.args.get('executor', '').strip()
        dfrom = request.args.get('date_from', '').strip()
        dto   = request.args.get('date_to',   '').strip()
        sort  = request.args.get('sort', 'created_desc')
        q     = Ticket.query
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
        executors = User.query.filter_by(role='support', is_deleted=False).order_by(User.name).all()

        return render_template('search.html', tickets=tickets, executors=executors,
                               executor_name=name, date_from=dfrom, date_to=dto, current_sort=sort)
