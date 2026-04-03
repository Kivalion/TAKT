import enum
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from takt.app.extensions import db


class ModuleNameEnum(enum.Enum):
    crm = 'crm'
    ticketing = 'ticketing'
    tasks = 'tasks'
    projects = 'projects'
    devices = 'devices'
    billing = 'billing'


class Tenant(db.Model):
    __tablename__ = 'tenants'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(60), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    modules = db.relationship('TenantModule', backref='tenant', lazy='dynamic')
    subscriptions = db.relationship('TenantSubscription', backref='tenant', lazy='dynamic')
    invoices = db.relationship('Invoice', backref='tenant', lazy='dynamic')

    def get_enabled_modules(self):
        return [m.module_name for m in self.modules if m.is_enabled]

    def is_module_enabled(self, module_name):
        m = TenantModule.query.filter_by(
            tenant_id=self.id, module_name=module_name, is_enabled=True
        ).first()
        return m is not None

    def __repr__(self):
        return f'<Tenant {self.slug}>'


class TenantModule(db.Model):
    __tablename__ = 'tenant_modules'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('public.tenants.id'), nullable=False)
    module_name = db.Column(db.String(50), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'module_name', name='uq_tenant_module'),
        {'schema': 'public'},
    )


class SuperAdminUser(UserMixin, db.Model):
    __tablename__ = 'super_admin_users'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f'admin:{self.id}'

    def __repr__(self):
        return f'<SuperAdminUser {self.username}>'


class ImpersonationLog(db.Model):
    __tablename__ = 'impersonation_logs'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    super_admin_id = db.Column(db.Integer, db.ForeignKey('public.super_admin_users.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('public.tenants.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)

    super_admin = db.relationship('SuperAdminUser', backref='impersonation_logs')
    tenant = db.relationship('Tenant', backref='impersonation_logs')


# MSP Billing (super admin bills tenants)

class BillingPlan(db.Model):
    __tablename__ = 'billing_plans'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price_monthly = db.Column(db.Numeric(10, 2), nullable=False)
    price_yearly = db.Column(db.Numeric(10, 2), nullable=False)

    subscriptions = db.relationship('TenantSubscription', backref='plan', lazy='dynamic')


class TenantSubscription(db.Model):
    __tablename__ = 'tenant_subscriptions'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('public.tenants.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('public.billing_plans.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='active')  # active/cancelled/past_due
    billing_cycle = db.Column(db.String(20), default='monthly')  # monthly/yearly


class Invoice(db.Model):
    __tablename__ = 'invoices'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('public.tenants.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default='draft')  # draft/sent/paid/overdue
    issued_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    paid_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    line_items = db.relationship('InvoiceLineItem', backref='invoice', cascade='all, delete-orphan')


class InvoiceLineItem(db.Model):
    __tablename__ = 'invoice_line_items'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('public.invoices.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
