from flask import Blueprint

dashboard_bp = Blueprint('dashboard', __name__)

from takt.app.blueprints.dashboard import routes  # noqa
