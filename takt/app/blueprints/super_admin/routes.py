from datetime import datetime
from flask import (
    render_template, redirect, url_for, flash, request, session, g
)
from flask_login import login_required, current_user
from takt.app.blueprints.super_admin import super_admin_bp
from takt.app.blueprints.super_admin.forms import (
    TenantForm, BillingPlanForm, TenantSubscriptionForm, InvoiceForm
)
from takt.app.extensions import db
from takt.app.middleware.module_guard import super_admin_required

ALL_MODULES = ['crm', 'ticketing', 'tasks', 'projects', 'devices', 'billing']


# ── Dashboard ─────────────────────────────────────────────────────────────────

@super_admin_bp.route('/')
@login_required
@super_admin_required
def dashboard():
    from takt.app.models.public import Tenant, Invoice
    tenants = Tenant.query.order_by(Tenant.name).all()
    outstanding = Invoice.query.filter(Invoice.status.in_(['sent', 'overdue'])).count()
    return render_template(
        'super_admin/dashboard.html',
        tenants=tenants,
        outstanding=outstanding,
    )


# ── Tenant management ─────────────────────────────────────────────────────────

@super_admin_bp.route('/tenants')
@login_required
@super_admin_required
def tenants():
    from takt.app.models.public import Tenant
    page = request.args.get('page', 1, type=int)
    tenants = Tenant.query.order_by(Tenant.name).paginate(page=page, per_page=25, error_out=False)
    return render_template('super_admin/tenants.html', tenants=tenants)


@super_admin_bp.route('/tenants/new', methods=['GET', 'POST'])
@login_required
@super_admin_required
def tenant_new():
    from takt.app.models.public import Tenant, TenantModule
    form = TenantForm()
    if form.validate_on_submit():
        tenant = Tenant(
            name=form.name.data,
            slug=form.slug.data,
            is_active=form.is_active.data,
        )
        db.session.add(tenant)
        db.session.flush()  # get tenant.id

        # Save module flags
        for mod in ALL_MODULES:
            tm = TenantModule(
                tenant_id=tenant.id,
                module_name=mod,
                is_enabled=(mod in (form.modules.data or [])),
            )
            db.session.add(tm)

        db.session.commit()

        # Provision tenant schema
        _provision_tenant_schema(tenant.slug)

        flash(f'Tenant "{tenant.name}" created.', 'success')
        return redirect(url_for('super_admin.tenants'))
    return render_template('super_admin/tenant_form.html', form=form, title='New Tenant')


@super_admin_bp.route('/tenants/<int:tenant_id>/edit', methods=['GET', 'POST'])
@login_required
@super_admin_required
def tenant_edit(tenant_id):
    from takt.app.models.public import Tenant, TenantModule
    tenant = Tenant.query.get_or_404(tenant_id)
    enabled = [m.module_name for m in tenant.modules if m.is_enabled]
    form = TenantForm(obj=tenant)
    if request.method == 'GET':
        form.modules.data = enabled

    if form.validate_on_submit():
        tenant.name = form.name.data
        tenant.slug = form.slug.data
        tenant.is_active = form.is_active.data

        # Update modules
        for mod in ALL_MODULES:
            tm = TenantModule.query.filter_by(tenant_id=tenant.id, module_name=mod).first()
            if tm:
                tm.is_enabled = (mod in (form.modules.data or []))
            else:
                db.session.add(TenantModule(
                    tenant_id=tenant.id,
                    module_name=mod,
                    is_enabled=(mod in (form.modules.data or [])),
                ))
        db.session.commit()
        flash('Tenant updated.', 'success')
        return redirect(url_for('super_admin.tenants'))
    return render_template('super_admin/tenant_form.html', form=form, title='Edit Tenant', tenant=tenant)


@super_admin_bp.route('/tenants/<int:tenant_id>/deactivate', methods=['POST'])
@login_required
@super_admin_required
def tenant_deactivate(tenant_id):
    from takt.app.models.public import Tenant
    tenant = Tenant.query.get_or_404(tenant_id)
    tenant.is_active = False
    db.session.commit()
    flash(f'Tenant "{tenant.name}" deactivated.', 'warning')
    return redirect(url_for('super_admin.tenants'))


@super_admin_bp.route('/tenants/<int:tenant_id>/activate', methods=['POST'])
@login_required
@super_admin_required
def tenant_activate(tenant_id):
    from takt.app.models.public import Tenant
    tenant = Tenant.query.get_or_404(tenant_id)
    tenant.is_active = True
    db.session.commit()
    flash(f'Tenant "{tenant.name}" activated.', 'success')
    return redirect(url_for('super_admin.tenants'))


# ── Impersonation ─────────────────────────────────────────────────────────────

@super_admin_bp.route('/tenants/<int:tenant_id>/impersonate', methods=['POST'])
@login_required
@super_admin_required
def impersonate(tenant_id):
    from takt.app.models.public import Tenant, ImpersonationLog
    tenant = Tenant.query.get_or_404(tenant_id)
    log = ImpersonationLog(
        super_admin_id=current_user.id,
        tenant_id=tenant.id,
        started_at=datetime.utcnow(),
    )
    db.session.add(log)
    db.session.commit()
    session['impersonating'] = True
    session['impersonating_log_id'] = log.id
    flash(f'Now impersonating {tenant.name}.', 'warning')
    return redirect(url_for('dashboard.index', tenant_slug=tenant.slug))


@super_admin_bp.route('/stop-impersonation', methods=['POST'])
@login_required
def stop_impersonation():
    from takt.app.models.public import ImpersonationLog
    log_id = session.pop('impersonating_log_id', None)
    session.pop('impersonating', None)
    if log_id:
        log = ImpersonationLog.query.get(log_id)
        if log:
            log.ended_at = datetime.utcnow()
            db.session.commit()
    flash('Impersonation ended.', 'info')
    return redirect(url_for('super_admin.dashboard'))


# ── Billing plans ─────────────────────────────────────────────────────────────

@super_admin_bp.route('/billing/plans')
@login_required
@super_admin_required
def billing_plans():
    from takt.app.models.public import BillingPlan
    plans = BillingPlan.query.order_by(BillingPlan.name).all()
    return render_template('super_admin/billing_plans.html', plans=plans)


@super_admin_bp.route('/billing/plans/new', methods=['GET', 'POST'])
@login_required
@super_admin_required
def billing_plan_new():
    from takt.app.models.public import BillingPlan
    form = BillingPlanForm()
    if form.validate_on_submit():
        plan = BillingPlan(
            name=form.name.data,
            description=form.description.data,
            price_monthly=form.price_monthly.data,
            price_yearly=form.price_yearly.data,
        )
        db.session.add(plan)
        db.session.commit()
        flash('Billing plan created.', 'success')
        return redirect(url_for('super_admin.billing_plans'))
    return render_template('super_admin/billing_plan_form.html', form=form, title='New Plan')


@super_admin_bp.route('/billing/plans/<int:plan_id>/edit', methods=['GET', 'POST'])
@login_required
@super_admin_required
def billing_plan_edit(plan_id):
    from takt.app.models.public import BillingPlan
    plan = BillingPlan.query.get_or_404(plan_id)
    form = BillingPlanForm(obj=plan)
    if form.validate_on_submit():
        plan.name = form.name.data
        plan.description = form.description.data
        plan.price_monthly = form.price_monthly.data
        plan.price_yearly = form.price_yearly.data
        db.session.commit()
        flash('Plan updated.', 'success')
        return redirect(url_for('super_admin.billing_plans'))
    return render_template('super_admin/billing_plan_form.html', form=form, title='Edit Plan', plan=plan)


# ── MSP Invoices ──────────────────────────────────────────────────────────────

@super_admin_bp.route('/billing/invoices')
@login_required
@super_admin_required
def msp_invoices():
    from takt.app.models.public import Invoice, Tenant
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    tenant_id = request.args.get('tenant_id', '', type=str)
    q = Invoice.query
    if status:
        q = q.filter(Invoice.status == status)
    if tenant_id:
        q = q.filter(Invoice.tenant_id == int(tenant_id))
    invoices = q.order_by(Invoice.issued_date.desc()).paginate(page=page, per_page=25, error_out=False)
    tenants = Tenant.query.order_by(Tenant.name).all()
    return render_template('super_admin/msp_invoices.html', invoices=invoices, tenants=tenants,
                           status=status, tenant_id=tenant_id)


@super_admin_bp.route('/billing/invoices/new', methods=['GET', 'POST'])
@login_required
@super_admin_required
def msp_invoice_new():
    from takt.app.models.public import Invoice, Tenant
    form = InvoiceForm()
    form.tenant_id.choices = [(t.id, t.name) for t in Tenant.query.order_by(Tenant.name)]
    if form.validate_on_submit():
        inv = Invoice(
            tenant_id=form.tenant_id.data,
            amount=form.amount.data,
            status=form.status.data,
            issued_date=form.issued_date.data,
            due_date=form.due_date.data,
            paid_date=form.paid_date.data,
            notes=form.notes.data,
        )
        db.session.add(inv)
        db.session.commit()
        flash('Invoice created.', 'success')
        return redirect(url_for('super_admin.msp_invoices'))
    return render_template('super_admin/msp_invoice_form.html', form=form, title='New Invoice')


@super_admin_bp.route('/billing/invoices/<int:inv_id>/edit', methods=['GET', 'POST'])
@login_required
@super_admin_required
def msp_invoice_edit(inv_id):
    from takt.app.models.public import Invoice, Tenant
    inv = Invoice.query.get_or_404(inv_id)
    form = InvoiceForm(obj=inv)
    form.tenant_id.choices = [(t.id, t.name) for t in Tenant.query.order_by(Tenant.name)]
    if form.validate_on_submit():
        inv.tenant_id = form.tenant_id.data
        inv.amount = form.amount.data
        inv.status = form.status.data
        inv.issued_date = form.issued_date.data
        inv.due_date = form.due_date.data
        inv.paid_date = form.paid_date.data
        inv.notes = form.notes.data
        db.session.commit()
        flash('Invoice updated.', 'success')
        return redirect(url_for('super_admin.msp_invoices'))
    return render_template('super_admin/msp_invoice_form.html', form=form, title='Edit Invoice', inv=inv)


@super_admin_bp.route('/billing/invoices/<int:inv_id>/delete', methods=['POST'])
@login_required
@super_admin_required
def msp_invoice_delete(inv_id):
    from takt.app.models.public import Invoice
    inv = Invoice.query.get_or_404(inv_id)
    db.session.delete(inv)
    db.session.commit()
    flash('Invoice deleted.', 'success')
    return redirect(url_for('super_admin.msp_invoices'))


# ── Tenant subscriptions ──────────────────────────────────────────────────────

@super_admin_bp.route('/tenants/<int:tenant_id>/subscription', methods=['GET', 'POST'])
@login_required
@super_admin_required
def tenant_subscription(tenant_id):
    from takt.app.models.public import Tenant, TenantSubscription, BillingPlan
    tenant = Tenant.query.get_or_404(tenant_id)
    sub = TenantSubscription.query.filter_by(tenant_id=tenant_id).first()
    form = TenantSubscriptionForm(obj=sub)
    form.plan_id.choices = [(p.id, p.name) for p in BillingPlan.query.order_by(BillingPlan.name)]
    if form.validate_on_submit():
        if sub:
            sub.plan_id = form.plan_id.data
            sub.start_date = form.start_date.data
            sub.end_date = form.end_date.data
            sub.status = form.status.data
            sub.billing_cycle = form.billing_cycle.data
        else:
            sub = TenantSubscription(
                tenant_id=tenant_id,
                plan_id=form.plan_id.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                status=form.status.data,
                billing_cycle=form.billing_cycle.data,
            )
            db.session.add(sub)
        db.session.commit()
        flash('Subscription saved.', 'success')
        return redirect(url_for('super_admin.tenants'))
    return render_template('super_admin/tenant_subscription.html', form=form, tenant=tenant, sub=sub)


# ── Impersonation log ─────────────────────────────────────────────────────────

@super_admin_bp.route('/impersonation-log')
@login_required
@super_admin_required
def impersonation_log():
    from takt.app.models.public import ImpersonationLog
    page = request.args.get('page', 1, type=int)
    logs = ImpersonationLog.query.order_by(
        ImpersonationLog.started_at.desc()
    ).paginate(page=page, per_page=25, error_out=False)
    return render_template('super_admin/impersonation_log.html', logs=logs)


# ── Helper ────────────────────────────────────────────────────────────────────

def _provision_tenant_schema(slug):
    """Create the schema and tables for a new tenant."""
    from sqlalchemy import text, MetaData
    from takt.app.models import tenant as tenant_module
    schema_name = f'tenant_{slug}'
    with db.engine.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        conn.execute(text(f'SET search_path TO "{schema_name}", public'))
        # Reflect tenant model tables and create in schema
        meta = MetaData(schema=None)
        # Get all tenant tables from SQLAlchemy metadata
        tenant_tables = [
            t for t in db.metadata.sorted_tables
            if t.schema is None  # No schema = tenant tables
        ]
        for table in tenant_tables:
            # Clone table with schema set to tenant schema
            from sqlalchemy import Table
            cloned = table.tometadata(MetaData(), schema=schema_name)
            try:
                cloned.create(conn, checkfirst=True)
            except Exception:
                pass
        conn.commit()
