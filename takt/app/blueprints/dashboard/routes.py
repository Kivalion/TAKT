from datetime import date, timedelta
from flask import render_template, g
from flask_login import login_required
from takt.app.blueprints.dashboard import dashboard_bp


@dashboard_bp.route('/')
@login_required
def index(tenant_slug):
    enabled = g.tenant.get_enabled_modules()
    stats = {}

    if 'ticketing' in enabled:
        from takt.app.models.tenant import Ticket
        stats['open_tickets'] = Ticket.query.filter_by(status='open').count()
        stats['inprogress_tickets'] = Ticket.query.filter_by(status='in-progress').count()

    if 'tasks' in enabled:
        from takt.app.models.tenant import Task
        today = date.today()
        week_ahead = today + timedelta(days=7)
        stats['tasks_today'] = Task.query.filter(
            Task.due_date == today, Task.status != 'done'
        ).count()
        stats['tasks_overdue'] = Task.query.filter(
            Task.due_date < today, Task.status != 'done'
        ).count()
        stats['tasks_week'] = Task.query.filter(
            Task.due_date > today, Task.due_date <= week_ahead, Task.status != 'done'
        ).count()
        stats['my_tasks'] = Task.query.filter_by(
            assigned_to=None  # will be filtered in template per current_user
        ).count()

    if 'crm' in enabled:
        from takt.app.models.tenant import Contact
        stats['contacts'] = Contact.query.count()

    if 'devices' in enabled:
        from takt.app.models.tenant import Device
        stats['devices_active'] = Device.query.filter_by(status='active').count()

    if 'billing' in enabled:
        from takt.app.models.tenant import CustomerInvoice
        stats['invoices_outstanding'] = CustomerInvoice.query.filter(
            CustomerInvoice.status.in_(['sent', 'overdue'])
        ).count()

    # Recent tickets
    recent_tickets = []
    if 'ticketing' in enabled:
        from takt.app.models.tenant import Ticket
        recent_tickets = Ticket.query.order_by(
            Ticket.updated_at.desc()
        ).limit(5).all()

    # Today's tasks
    my_tasks_today = []
    if 'tasks' in enabled:
        from flask_login import current_user
        from takt.app.models.tenant import Task
        today = date.today()
        my_tasks_today = Task.query.filter(
            Task.assigned_to == current_user.id,
            Task.due_date == today,
            Task.status != 'done',
        ).all()

    return render_template(
        'dashboard/index.html',
        tenant_slug=tenant_slug,
        enabled=enabled,
        stats=stats,
        recent_tickets=recent_tickets,
        my_tasks_today=my_tasks_today,
    )
