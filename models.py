from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), default='user')  # user / support / admin
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted    = db.Column(db.Boolean, default=False)  # Флаг: пользователь удалён

    def set_password(self, password):
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()


class Ticket(db.Model):
    __tablename__ = 'tickets'
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text,        nullable=False)
    priority    = db.Column(db.String(20),  default='medium')  # low / medium / high
    status      = db.Column(db.String(20),  default='new')     # new / in_progress / resolved / closed
    created_at  = db.Column(db.DateTime,    default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime,    default=datetime.utcnow)
    author_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    executor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    author   = db.relationship('User', foreign_keys=[author_id],   backref='created_tickets')
    executor = db.relationship('User', foreign_keys=[executor_id], backref='assigned_tickets')
