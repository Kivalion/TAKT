from flask import render_template, redirect, url_for, flash, request, g
from flask_login import login_required, current_user
from takt.app.blueprints.projects import projects_bp
from takt.app.blueprints.projects.forms import ProjectForm, AddMemberForm
from takt.app.extensions import db
from takt.app.middleware.module_guard import module_required


@projects_bp.route('/')
@login_required
@module_required('projects')
def project_list(tenant_slug):
    from takt.app.models.tenant import Project
    status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    q = Project.query
    if status:
        q = q.filter(Project.status == status)
    projects = q.order_by(Project.created_at.desc()).paginate(page=page, per_page=25, error_out=False)
    return render_template('projects/project_list.html', projects=projects,
                           status=status, tenant_slug=tenant_slug)


@projects_bp.route('/<int:project_id>')
@login_required
@module_required('projects')
def project_detail(tenant_slug, project_id):
    from takt.app.models.tenant import Project, Ticket, Task, TimeEntry, TaskTimeEntry
    project = Project.query.get_or_404(project_id)
    add_member_form = AddMemberForm()

    # Stats
    open_tickets = Ticket.query.filter_by(project_id=project_id).filter(
        Ticket.status.notin_(['resolved', 'closed'])
    ).count()
    open_tasks = Task.query.filter_by(project_id=project_id).filter(
        Task.status != 'done'
    ).count()

    # Total time from tickets
    ticket_ids = [t.id for t in project.tickets]
    task_ids = [t.id for t in project.tasks]
    ticket_minutes = db.session.query(db.func.sum(TimeEntry.minutes)).filter(
        TimeEntry.ticket_id.in_(ticket_ids)
    ).scalar() or 0
    task_minutes = db.session.query(db.func.sum(TaskTimeEntry.duration_minutes)).filter(
        TaskTimeEntry.task_id.in_(task_ids)
    ).scalar() or 0
    total_minutes = ticket_minutes + task_minutes

    return render_template('projects/project_detail.html', project=project,
                           add_member_form=add_member_form,
                           open_tickets=open_tickets, open_tasks=open_tasks,
                           total_minutes=total_minutes, tenant_slug=tenant_slug)


@projects_bp.route('/new', methods=['GET', 'POST'])
@login_required
@module_required('projects')
def project_new(tenant_slug):
    from takt.app.models.tenant import Project
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(
            name=form.name.data,
            description=form.description.data,
            status=form.status.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            site_id=form.site_id.data or None,
            manager_id=form.manager_id.data or None,
        )
        db.session.add(project)
        db.session.commit()
        flash('Project created.', 'success')
        return redirect(url_for('projects.project_detail', tenant_slug=tenant_slug, project_id=project.id))
    return render_template('projects/project_form.html', form=form, title='New Project', tenant_slug=tenant_slug)


@projects_bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@module_required('projects')
def project_edit(tenant_slug, project_id):
    from takt.app.models.tenant import Project
    project = Project.query.get_or_404(project_id)
    form = ProjectForm(obj=project)
    if form.validate_on_submit():
        project.name = form.name.data
        project.description = form.description.data
        project.status = form.status.data
        project.start_date = form.start_date.data
        project.end_date = form.end_date.data
        project.site_id = form.site_id.data or None
        project.manager_id = form.manager_id.data or None
        db.session.commit()
        flash('Project updated.', 'success')
        return redirect(url_for('projects.project_detail', tenant_slug=tenant_slug, project_id=project.id))
    return render_template('projects/project_form.html', form=form, title='Edit Project',
                           project=project, tenant_slug=tenant_slug)


@projects_bp.route('/<int:project_id>/delete', methods=['POST'])
@login_required
@module_required('projects')
def project_delete(tenant_slug, project_id):
    from takt.app.models.tenant import Project
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted.', 'success')
    return redirect(url_for('projects.project_list', tenant_slug=tenant_slug))


@projects_bp.route('/<int:project_id>/members/add', methods=['POST'])
@login_required
@module_required('projects')
def add_member(tenant_slug, project_id):
    from takt.app.models.tenant import Project, ProjectMember
    project = Project.query.get_or_404(project_id)
    form = AddMemberForm()
    if form.validate_on_submit():
        existing = ProjectMember.query.filter_by(
            project_id=project_id, user_id=form.user_id.data
        ).first()
        if not existing:
            member = ProjectMember(
                project_id=project_id,
                user_id=form.user_id.data,
                role=form.role.data,
            )
            db.session.add(member)
            db.session.commit()
            flash('Member added.', 'success')
        else:
            flash('User is already a member.', 'warning')
    return redirect(url_for('projects.project_detail', tenant_slug=tenant_slug, project_id=project_id))


@projects_bp.route('/<int:project_id>/members/<int:member_id>/remove', methods=['POST'])
@login_required
@module_required('projects')
def remove_member(tenant_slug, project_id, member_id):
    from takt.app.models.tenant import ProjectMember
    member = ProjectMember.query.get_or_404(member_id)
    db.session.delete(member)
    db.session.commit()
    flash('Member removed.', 'success')
    return redirect(url_for('projects.project_detail', tenant_slug=tenant_slug, project_id=project_id))
