from flask import g, abort, session, request
from sqlalchemy import text
from takt.app.extensions import db


def init_tenant_middleware(app):
    @app.before_request
    def resolve_tenant():
        g.tenant = None
        g.tenant_schema = None

        # Check for impersonation in super admin session
        if request.path.startswith('/t/'):
            parts = request.path.lstrip('/').split('/')
            # parts[0] == 't', parts[1] == slug
            if len(parts) < 2:
                abort(404)
            slug = parts[1]
            _load_tenant(slug)
        else:
            # Public schema mode — set search_path to public only
            try:
                db.session.execute(text('SET search_path TO public'))
            except Exception:
                pass

    def _load_tenant(slug):
        from takt.app.models.public import Tenant
        # Ensure public schema is searched when loading tenant registry
        db.session.execute(text('SET search_path TO public'))
        tenant = Tenant.query.filter_by(slug=slug, is_active=True).first()
        if tenant is None:
            abort(404)
        g.tenant = tenant
        g.tenant_schema = f'tenant_{slug}'
        # Switch search_path so subsequent ORM queries hit the tenant schema
        db.session.execute(text(f'SET search_path TO tenant_{slug}, public'))
