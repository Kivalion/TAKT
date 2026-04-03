from flask import render_template, redirect, url_for, flash, request, g
from flask_login import login_required, current_user
from takt.app.blueprints.ticketing import ticketing_bp
from takt.app.blueprints.ticketing.forms import TicketForm, CommentForm, TimeEntryForm
from takt.app.extensions import db
from takt.app.middleware.module_guard import module_required


@ticketing_bp.route('/')
@login_required
@module_required('ticketing')
def tickets(tenant_slug):
    from takt.app.models.tenant import Ticket, User, Site
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    ticket_type = request.args.get('type', '')
    assignee = request.args.get('assignee', '', type=str)
    site_id = request.args.get('site_id', '', type=str)
    page = request.args.get('page', 1, type=int)

    query = Ticket.query
    if q:
        like = f'%{q}%'
        query = query.filter(
            db.or_(Ticket.title.ilike(like), Ticket.description.ilike(like))
        )
    if status:
        query = query.filter(Ticket.status == status)
    if priority:
        query = query.filter(Ticket.priority == priority)
    if ticket_type:
        query = query.filter(Ticket.type == ticket_type)
    if assignee:
        query = query.filter(Ticket.assigned_to == int(assignee))
    if site_id:
        query = query.filter(Ticket.site_id == int(site_id))

    tickets = query.order_by(Ticket.updated_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    sites = Site.query.filter_by(is_active=True).order_by(Site.name).all()
    return render_template('ticketing/tickets.html', tickets=tickets, users=users, sites=sites,
                           q=q, status=status, priority=priority, ticket_type=ticket_type,
                           assignee=assignee, site_id=site_id, tenant_slug=tenant_slug)


@ticketing_bp.route('/<int:ticket_id>')
@login_required
@module_required('ticketing')
def ticket_detail(tenant_slug, ticket_id):
    from takt.app.models.tenant import Ticket
    ticket = Ticket.query.get_or_404(ticket_id)
    comment_form = CommentForm()
    time_form = TimeEntryForm()
    return render_template('ticketing/ticket_detail.html', ticket=ticket,
                           comment_form=comment_form, time_form=time_form,
                           tenant_slug=tenant_slug)


@ticketing_bp.route('/new', methods=['GET', 'POST'])
@login_required
@module_required('ticketing')
def ticket_new(tenant_slug):
    from takt.app.models.tenant import Ticket
    form = TicketForm()
    if form.validate_on_submit():
        ticket = Ticket(
            title=form.title.data,
            description=form.description.data,
            status=form.status.data,
            priority=form.priority.data,
            type=form.type.data,
            assigned_to=form.assigned_to.data or None,
            site_id=form.site_id.data or None,
            project_id=form.project_id.data or None,
            created_by=current_user.id,
        )
        db.session.add(ticket)
        db.session.commit()
        flash('Ticket created.', 'success')
        return redirect(url_for('ticketing.ticket_detail', tenant_slug=tenant_slug, ticket_id=ticket.id))
    return render_template('ticketing/ticket_form.html', form=form, title='New Ticket', tenant_slug=tenant_slug)


@ticketing_bp.route('/<int:ticket_id>/edit', methods=['GET', 'POST'])
@login_required
@module_required('ticketing')
def ticket_edit(tenant_slug, ticket_id):
    from takt.app.models.tenant import Ticket
    ticket = Ticket.query.get_or_404(ticket_id)
    form = TicketForm(obj=ticket)
    if form.validate_on_submit():
        ticket.title = form.title.data
        ticket.description = form.description.data
        ticket.status = form.status.data
        ticket.priority = form.priority.data
        ticket.type = form.type.data
        ticket.assigned_to = form.assigned_to.data or None
        ticket.site_id = form.site_id.data or None
        ticket.project_id = form.project_id.data or None
        db.session.commit()
        flash('Ticket updated.', 'success')
        return redirect(url_for('ticketing.ticket_detail', tenant_slug=tenant_slug, ticket_id=ticket.id))
    return render_template('ticketing/ticket_form.html', form=form, title='Edit Ticket',
                           ticket=ticket, tenant_slug=tenant_slug)


@ticketing_bp.route('/<int:ticket_id>/delete', methods=['POST'])
@login_required
@module_required('ticketing')
def ticket_delete(tenant_slug, ticket_id):
    from takt.app.models.tenant import Ticket
    ticket = Ticket.query.get_or_404(ticket_id)
    db.session.delete(ticket)
    db.session.commit()
    flash('Ticket deleted.', 'success')
    return redirect(url_for('ticketing.tickets', tenant_slug=tenant_slug))


@ticketing_bp.route('/<int:ticket_id>/comment', methods=['POST'])
@login_required
@module_required('ticketing')
def ticket_comment(tenant_slug, ticket_id):
    from takt.app.models.tenant import Ticket, TicketComment
    ticket = Ticket.query.get_or_404(ticket_id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = TicketComment(
            ticket_id=ticket.id,
            user_id=current_user.id,
            body=form.body.data,
        )
        db.session.add(comment)
        db.session.commit()
        flash('Comment added.', 'success')
    return redirect(url_for('ticketing.ticket_detail', tenant_slug=tenant_slug, ticket_id=ticket_id))


@ticketing_bp.route('/<int:ticket_id>/time', methods=['POST'])
@login_required
@module_required('ticketing')
def ticket_log_time(tenant_slug, ticket_id):
    from takt.app.models.tenant import Ticket, TimeEntry
    ticket = Ticket.query.get_or_404(ticket_id)
    form = TimeEntryForm()
    if form.validate_on_submit():
        entry = TimeEntry(
            ticket_id=ticket.id,
            user_id=current_user.id,
            minutes=form.minutes.data,
            note=form.note.data,
        )
        db.session.add(entry)
        db.session.commit()
        flash(f'{form.minutes.data} minutes logged.', 'success')
    return redirect(url_for('ticketing.ticket_detail', tenant_slug=tenant_slug, ticket_id=ticket_id))
