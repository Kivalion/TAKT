from flask import Blueprint

billing_bp = Blueprint('billing', __name__)

from takt.app.blueprints.billing import routes  # noqa
