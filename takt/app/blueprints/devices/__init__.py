from flask import Blueprint

devices_bp = Blueprint('devices', __name__)

from takt.app.blueprints.devices import routes  # noqa
