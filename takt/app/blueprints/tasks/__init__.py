from flask import Blueprint

tasks_bp = Blueprint('tasks', __name__)

from takt.app.blueprints.tasks import routes  # noqa
