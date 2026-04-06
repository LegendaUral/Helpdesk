"""API маршруты"""
from flask import request, jsonify, session, redirect, url_for, flash
from datetime import datetime
from sqlalchemy import case
from models import db, Ticket, Message, User


def setup_api_routes(app, auth_required):
    """Регистрирует API маршруты"""
    
    @app.route('/tickets/<int:ticket_id>/message', methods=['POST'])
    def add_message(ticket_id):
        err = auth_required()
        if err: return err
        
        ticket = Ticket.query.get_or_404(ticket_id)
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
        err = auth_required()
        if err: return err
        
        ticket = Ticket.query.get_or_404(ticket_id)
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

    @app.route('/api/tickets')
    def api_tickets():
        err = auth_required()
        if err: return err
        
        role, uid = session['user_role'], session['user_id']
        sort = request.args.get('sort', 'created_desc')
        
        if role == 'admin':
            q = Ticket.query
        elif role == 'support':
            from sqlalchemy import or_
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

    @app.route('/service-worker.js')
    def service_worker():
        import os
        from flask import send_from_directory, Response
        sw_path = os.path.join(os.path.dirname(__file__), 'static', 'service-worker.js')
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='application/javascript')
