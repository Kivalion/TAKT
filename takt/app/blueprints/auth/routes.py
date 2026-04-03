from flask import (
    render_template, redirect, url_for, flash, request, g, session
)
from flask_login import login_user, logout_user, login_required, current_user
from takt.app.blueprints.auth import auth_bp
from takt.app.blueprints.auth.forms import LoginForm, UserForm, SiteForm
from takt.app.extensions import db
from takt.app.middleware.module_guard import admin_required


# ── Login / logout ────────────────────────────────────────────────────────────

@auth_bp.route('/t/<tenant_slug>/login', methods=['GET', 'POST'])
def login(tenant_slug):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index', tenant_slug=tenant_slug))
    form = LoginForm()
    if form.validate_on_submit():
        from takt.app.models.tenant import User
        user = User.query.filter_by(username=form.username.data, is_active=True).first()
        if user and user.check_password(form.password.data):
            user._tenant_slug = tenant_slug
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index', tenant_slug=tenant_slug))
        flash('Invalid username or password.', 'danger')
    return render_template('auth/login.html', form=form, tenant_slug=tenant_slug)


@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('super_admin.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        from takt.app.models.public import SuperAdminUser
        user = SuperAdminUser.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(url_for('super_admin.dashboard'))
        flash('Invalid credentials.', 'danger')
    return render_template('auth/admin_login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    tenant_slug = None
    if g.tenant:
        tenant_slug = g.tenant.slug
    # End impersonation if active
    if session.pop('impersonating', None):
        from takt.app.models.public import ImpersonationLog
        from datetime import datetime
        log = ImpersonationLog.query.filter_by(
            ended_at=None
        ).order_by(ImpersonationLog.id.desc()).first()
        if log:
            log.ended_at = datetime.utcnow()
            db.session.commit()
    logout_user()
    if tenant_slug:
        return redirect(url_for('auth.login', tenant_slug=tenant_slug))
    return redirect(url_for('auth.admin_login'))


@auth_bp.route('/login')
def login_redirect():
    """Default login redirect for Flask-Login."""
    return redirect(url_for('auth.admin_login'))


# ── User management (tenant admin) ───────────────────────────────────────────

@auth_bp.route('/t/<tenant_slug>/users')
@login_required
@admin_required
def manage_users(tenant_slug):
    from takt.app.models.tenant import User
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.username).paginate(
        page=page, per_page=25, error_out=False
    )
    return render_template('auth/users.html', users=users, tenant_slug=tenant_slug)


@auth_bp.route('/t/<tenant_slug>/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def user_new(tenant_slug):
    from takt.app.models.tenant import User
    form = UserForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            is_active=form.is_active.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('User created.', 'success')
        return redirect(url_for('auth.manage_users', tenant_slug=tenant_slug))
    return render_template('auth/user_form.html', form=form, tenant_slug=tenant_slug, title='New User')


@auth_bp.route('/t/<tenant_slug>/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def user_edit(tenant_slug, user_id):
    from takt.app.models.tenant import User
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash('User updated.', 'success')
        return redirect(url_for('auth.manage_users', tenant_slug=tenant_slug))
    return render_template('auth/user_form.html', form=form, tenant_slug=tenant_slug, title='Edit User', user=user)


@auth_bp.route('/t/<tenant_slug>/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def user_delete(tenant_slug, user_id):
    from takt.app.models.tenant import User
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted.', 'success')
    return redirect(url_for('auth.manage_users', tenant_slug=tenant_slug))


# ── Site management (tenant admin) ───────────────────────────────────────────

@auth_bp.route('/t/<tenant_slug>/sites')
@login_required
@admin_required
def manage_sites(tenant_slug):
    from takt.app.models.tenant import Site
    page = request.args.get('page', 1, type=int)
    sites = Site.query.order_by(Site.name).paginate(
        page=page, per_page=25, error_out=False
    )
    return render_template('auth/sites.html', sites=sites, tenant_slug=tenant_slug)


@auth_bp.route('/t/<tenant_slug>/sites/new', methods=['GET', 'POST'])
@login_required
@admin_required
def site_new(tenant_slug):
    from takt.app.models.tenant import Site
    form = SiteForm()
    if form.validate_on_submit():
        site = Site(
            name=form.name.data,
            address=form.address.data,
            contact_email=form.contact_email.data,
            is_active=form.is_active.data,
        )
        db.session.add(site)
        db.session.commit()
        flash('Site created.', 'success')
        return redirect(url_for('auth.manage_sites', tenant_slug=tenant_slug))
    return render_template('auth/site_form.html', form=form, tenant_slug=tenant_slug, title='New Site')


@auth_bp.route('/t/<tenant_slug>/sites/<int:site_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def site_edit(tenant_slug, site_id):
    from takt.app.models.tenant import Site
    site = Site.query.get_or_404(site_id)
    form = SiteForm(obj=site)
    if form.validate_on_submit():
        site.name = form.name.data
        site.address = form.address.data
        site.contact_email = form.contact_email.data
        site.is_active = form.is_active.data
        db.session.commit()
        flash('Site updated.', 'success')
        return redirect(url_for('auth.manage_sites', tenant_slug=tenant_slug))
    return render_template('auth/site_form.html', form=form, tenant_slug=tenant_slug, title='Edit Site', site=site)


@auth_bp.route('/t/<tenant_slug>/sites/<int:site_id>/delete', methods=['POST'])
@login_required
@admin_required
def site_delete(tenant_slug, site_id):
    from takt.app.models.tenant import Site
    site = Site.query.get_or_404(site_id)
    db.session.delete(site)
    db.session.commit()
    flash('Site deleted.', 'success')
    return redirect(url_for('auth.manage_sites', tenant_slug=tenant_slug))
