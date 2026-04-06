"""Инициализация маршрутов"""
from .auth import setup_auth_routes
from .tickets import setup_tickets_routes
from .search import setup_search_routes
from .users import setup_users_routes
from .api import setup_api_routes


def register_routes(app, auth_required):
    """Регистрирует все маршруты приложения"""
    setup_auth_routes(app)
    setup_tickets_routes(app, auth_required)
    setup_search_routes(app, auth_required)
    setup_users_routes(app, auth_required)
    setup_api_routes(app, auth_required)
