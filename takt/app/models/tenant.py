from datetime import datetime
import bcrypt
from flask_login import UserMixin
from takt.app.extensions import db

# All tenant models live in the tenant schema, resolved via SET search_path
# They use schema=None so PostgreSQL search_path governs resolution.


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')  # admin/user
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # stored in session as "tenant:{slug}:{id}"
    _tenant_slug = None

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def get_id(self):
        slug = getattr(self, '_tenant_slug', '') or ''
        return f'tenant:{slug}:{self.id}'

    @property
    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username}>'


class Site(db.Model):
    __tablename__ = 'sites'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.Text, nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserSite(db.Model):
    __tablename__ = 'user_sites'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), primary_key=True)


# CRM

class Contact(db.Model):
    __tablename__ = 'contacts'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    company = db.Column(db.String(120), nullable=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    site = db.relationship('Site', backref='contacts', foreign_keys=[site_id])
    creator = db.relationship('User', backref='created_contacts', foreign_keys=[created_by])

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'


# Ticketing

class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='open')  # open/in-progress/on-hold/resolved/closed
    priority = db.Column(db.String(20), default='medium')  # low/medium/high/critical
    type = db.Column(db.String(20), default='incident')  # incident/request/change
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignee = db.relationship('User', backref='assigned_tickets', foreign_keys=[assigned_to])
    creator = db.relationship('User', backref='created_tickets', foreign_keys=[created_by])
    site = db.relationship('Site', backref='tickets', foreign_keys=[site_id])
    comments = db.relationship('TicketComment', backref='ticket', cascade='all, delete-orphan', order_by='TicketComment.created_at')
    time_entries = db.relationship('TimeEntry', backref='ticket', cascade='all, delete-orphan')

    @property
    def total_minutes(self):
        return sum(e.minutes for e in self.time_entries)


class TicketComment(db.Model):
    __tablename__ = 'ticket_comments'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', backref='ticket_comments', foreign_keys=[user_id])


class TimeEntry(db.Model):
    __tablename__ = 'time_entries'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    minutes = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='time_entries', foreign_keys=[user_id])


# Tasks

class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='todo')  # todo/in-progress/done/on-hold
    priority = db.Column(db.String(20), default='medium')  # low/medium/high
    due_date = db.Column(db.Date, nullable=True)
    estimated_minutes = db.Column(db.Integer, nullable=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    tags = db.Column(db.String(255), nullable=True)  # comma-separated
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_rule = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignee = db.relationship('User', backref='assigned_tasks', foreign_keys=[assigned_to])
    creator = db.relationship('User', backref='created_tasks', foreign_keys=[created_by])
    task_time_entries = db.relationship('TaskTimeEntry', backref='task', cascade='all, delete-orphan')

    @property
    def total_minutes(self):
        return sum(
            e.duration_minutes for e in self.task_time_entries if e.duration_minutes
        )

    @property
    def tag_list(self):
        if self.tags:
            return [t.strip() for t in self.tags.split(',') if t.strip()]
        return []

    @property
    def is_overdue(self):
        from datetime import date
        return self.due_date and self.due_date < date.today() and self.status not in ('done',)


class TaskTimeEntry(db.Model):
    __tablename__ = 'task_time_entries'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    note = db.Column(db.String(255), nullable=True)

    user = db.relationship('User', backref='task_time_entries', foreign_keys=[user_id])


class CalendarEvent(db.Model):
    __tablename__ = 'calendar_events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    linked_task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True)

    user = db.relationship('User', backref='calendar_events', foreign_keys=[user_id])
    linked_task = db.relationship('Task', backref='calendar_events', foreign_keys=[linked_task_id])


# Projects

class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='active')  # active/on-hold/completed
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    site = db.relationship('Site', backref='projects', foreign_keys=[site_id])
    manager = db.relationship('User', backref='managed_projects', foreign_keys=[manager_id])
    members = db.relationship('ProjectMember', backref='project', cascade='all, delete-orphan')
    tickets = db.relationship('Ticket', backref='project', foreign_keys='Ticket.project_id')
    tasks = db.relationship('Task', backref='project', foreign_keys='Task.project_id')


class ProjectMember(db.Model):
    __tablename__ = 'project_members'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50), default='member')

    user = db.relationship('User', backref='project_memberships', foreign_keys=[user_id])

    __table_args__ = (
        db.UniqueConstraint('project_id', 'user_id', name='uq_project_member'),
    )


# Devices

class Device(db.Model):
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(120), nullable=False)
    serial_number = db.Column(db.String(120), nullable=True)
    manufacturer = db.Column(db.String(120), nullable=True)
    model = db.Column(db.String(120), nullable=True)
    device_type = db.Column(db.String(30), default='workstation')  # workstation/server/network/printer/other
    os = db.Column(db.String(80), nullable=True)
    os_version = db.Column(db.String(80), nullable=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(20), default='active')  # active/inactive/decommissioned
    notes = db.Column(db.Text, nullable=True)
    registered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    site = db.relationship('Site', backref='devices', foreign_keys=[site_id])
    assigned_user = db.relationship('User', backref='assigned_devices', foreign_keys=[assigned_to])
    registered_by_user = db.relationship('User', backref='registered_devices', foreign_keys=[registered_by])
    tags = db.relationship('DeviceTag', backref='device', cascade='all, delete-orphan')


class DeviceTag(db.Model):
    __tablename__ = 'device_tags'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    tag = db.Column(db.String(60), nullable=False)


# Tenant Billing

class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    address = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subscriptions = db.relationship('CustomerSubscription', backref='customer', cascade='all, delete-orphan')
    invoices = db.relationship('CustomerInvoice', backref='customer', cascade='all, delete-orphan')


class CustomerSubscription(db.Model):
    __tablename__ = 'customer_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    plan_name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    billing_cycle = db.Column(db.String(20), default='monthly')  # monthly/yearly
    start_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='active')  # active/cancelled/paused


class CustomerInvoice(db.Model):
    __tablename__ = 'customer_invoices'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default='draft')  # draft/sent/paid/overdue
    issued_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    paid_date = db.Column(db.Date, nullable=True)

    line_items = db.relationship('CustomerInvoiceLineItem', backref='invoice', cascade='all, delete-orphan')


class CustomerInvoiceLineItem(db.Model):
    __tablename__ = 'customer_invoice_line_items'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('customer_invoices.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
