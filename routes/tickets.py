"""Маршруты управления заявками"""
from flask import render_template, request, redirect, url_for, session, flash
from datetime import datetime
from sqlalchemy import or_, case
from models import db, User, Ticket


def setup_tickets_routes(app, auth_required):
    """Регистрирует маршруты заявок"""
    
    @app.route('/')
    def index():
        err = auth_required()
        if err: return err
        role, uid = session['user_role'], session['user_id']
        sort = request.args.get('sort', 'created_desc')

        if role == 'admin':
            q = Ticket.query
        elif role == 'support':
            q = Ticket.query.filter(or_(Ticket.executor_id == uid, Ticket.executor_id.is_(None)))
        else:
            q = Ticket.query.filter_by(author_id=uid)

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
        return render_template('index.html', tickets=tickets, current_sort=sort)

    @app.route('/tickets/new', methods=['GET', 'POST'])
    def new_ticket():
        err = auth_required()
        if err: return err
        
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
        err = auth_required(role=['support', 'admin'])
        if err: return err
        ticket = Ticket.query.get_or_404(ticket_id)
        
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
        err = auth_required(role=['support', 'admin'])
        if err: return err
        ticket = Ticket.query.get_or_404(ticket_id)
        
        if ticket.executor_id != session['user_id'] and session['user_role'] != 'admin':
            flash('Вы не являетесь исполнителем.', 'danger')
            return redirect(url_for('ticket_detail', ticket_id=ticket_id))
        
        ticket.executor_id = None
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Заявка отпущена.', 'success')
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))
