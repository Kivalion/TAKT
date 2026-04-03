from flask import Blueprint

crm_bp = Blueprint('crm', __name__)

from takt.app.blueprints.crm import routes  # noqa
