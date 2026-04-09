import logging
from flask import Flask
from config import Config
from takt.app.extensions import db, login_manager, csrf, limiter
from takt.app.middleware.tenant import init_tenant_middleware

logger = logging.getLogger(__name__)


def create_app(config_class=Config):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_class)

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = 'auth.login_redirect'
    login_manager.login_message_category = 'warning'

    # User loader
    from takt.app.extensions import db as _db
    from sqlalchemy import text

    @login_manager.user_loader
    def load_user(user_id):
        if user_id.startswith('admin:'):
            from takt.app.models.public import SuperAdminUser
            uid = int(user_id.split(':')[1])
            return _db.session.get(SuperAdminUser, uid)
        elif user_id.startswith('tenant:'):
            from takt.app.models.tenant import User
            parts = user_id.split(':', 2)
            slug = parts[1]
            uid = int(parts[2])
            try:
                _db.session.execute(text(f'SET search_path TO tenant_{slug}, public'))
            except Exception as exc:
                logger.warning("Failed to set search_path for tenant '%s': %s", slug, exc)
            user = _db.session.get(User, uid)
            if user:
                user._tenant_slug = slug
            return user
        return None

    # Tenant middleware
    init_tenant_middleware(app)

    # Blueprints
    from takt.app.blueprints.auth import auth_bp
    from takt.app.blueprints.super_admin import super_admin_bp
    from takt.app.blueprints.dashboard import dashboard_bp
    from takt.app.blueprints.crm import crm_bp
    from takt.app.blueprints.ticketing import ticketing_bp
    from takt.app.blueprints.tasks import tasks_bp
    from takt.app.blueprints.projects import projects_bp
    from takt.app.blueprints.devices import devices_bp
    from takt.app.blueprints.billing import billing_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(super_admin_bp, url_prefix='/admin')
    app.register_blueprint(dashboard_bp, url_prefix='/t/<tenant_slug>/dashboard')
    app.register_blueprint(crm_bp, url_prefix='/t/<tenant_slug>/crm')
    app.register_blueprint(ticketing_bp, url_prefix='/t/<tenant_slug>/tickets')
    app.register_blueprint(tasks_bp, url_prefix='/t/<tenant_slug>/tasks')
    app.register_blueprint(projects_bp, url_prefix='/t/<tenant_slug>/projects')
    app.register_blueprint(devices_bp, url_prefix='/t/<tenant_slug>/devices')
    app.register_blueprint(billing_bp, url_prefix='/t/<tenant_slug>/billing')

    # Root redirect
    from flask import redirect, url_for
    @app.route('/')
    def index():
        return redirect(url_for('super_admin.dashboard'))

    # Health check — exempt from auth and rate limiting
    from flask import jsonify
    @app.route('/health')
    @limiter.exempt
    def health():
        checks = {'status': 'ok', 'database': 'ok'}
        try:
            db.session.execute(text('SELECT 1'))
        except Exception as exc:
            logger.error("Health check database failure: %s", exc)
            checks['database'] = 'unavailable'
            checks['status'] = 'degraded'
        return jsonify(checks), 200 if checks['status'] == 'ok' else 503

    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('errors/404.html'), 404

    return app
