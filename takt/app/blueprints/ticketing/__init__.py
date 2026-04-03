from flask import Blueprint

ticketing_bp = Blueprint('ticketing', __name__)

from takt.app.blueprints.ticketing import routes  # noqa
