import calendar as cal_module
from datetime import date, datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, g, session
from flask_login import login_required, current_user
from takt.app.blueprints.tasks import tasks_bp
from takt.app.blueprints.tasks.forms import TaskForm, ManualTimeForm, CalendarEventForm
from takt.app.extensions import db
from takt.app.middleware.module_guard import module_required


@tasks_bp.route('/')
@login_required
@module_required('tasks')
def task_list(tenant_slug):
    from takt.app.models.tenant import Task, User
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    tag = request.args.get('tag', '')
    assignee = request.args.get('assignee', '', type=str)
    page = request.args.get('page', 1, type=int)

    query = Task.query
    if q:
        query = query.filter(Task.title.ilike(f'%{q}%'))
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    if tag:
        query = query.filter(Task.tags.ilike(f'%{tag}%'))
    if assignee:
        query = query.filter(Task.assigned_to == int(assignee))

    tasks = query.order_by(Task.due_date.asc().nulls_last(), Task.priority.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    today = date.today()
    timer_task_id = session.get('timer_task_id')
    return render_template('tasks/task_list.html', tasks=tasks, users=users,
                           q=q, status=status, priority=priority, tag=tag, assignee=assignee,
                           tenant_slug=tenant_slug, today=today, timer_task_id=timer_task_id)


@tasks_bp.route('/<int:task_id>')
@login_required
@module_required('tasks')
def task_detail(tenant_slug, task_id):
    from takt.app.models.tenant import Task
    task = Task.query.get_or_404(task_id)
    time_form = ManualTimeForm()
    timer_task_id = session.get('timer_task_id')
    return render_template('tasks/task_detail.html', task=task, time_form=time_form,
                           tenant_slug=tenant_slug, timer_task_id=timer_task_id)


@tasks_bp.route('/new', methods=['GET', 'POST'])
@login_required
@module_required('tasks')
def task_new(tenant_slug):
    from takt.app.models.tenant import Task
    form = TaskForm()
    if form.validate_on_submit():
        task = Task(
            title=form.title.data,
            description=form.description.data,
            status=form.status.data,
            priority=form.priority.data,
            due_date=form.due_date.data,
            estimated_minutes=form.estimated_minutes.data,
            assigned_to=form.assigned_to.data or None,
            project_id=form.project_id.data or None,
            tags=form.tags.data,
            is_recurring=form.is_recurring.data,
            recurrence_rule=form.recurrence_rule.data,
            created_by=current_user.id,
        )
        db.session.add(task)
        db.session.commit()
        flash('Task created.', 'success')
        return redirect(url_for('tasks.task_detail', tenant_slug=tenant_slug, task_id=task.id))
    return render_template('tasks/task_form.html', form=form, title='New Task', tenant_slug=tenant_slug)


@tasks_bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
@module_required('tasks')
def task_edit(tenant_slug, task_id):
    from takt.app.models.tenant import Task
    task = Task.query.get_or_404(task_id)
    form = TaskForm(obj=task)
    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.status = form.status.data
        task.priority = form.priority.data
        task.due_date = form.due_date.data
        task.estimated_minutes = form.estimated_minutes.data
        task.assigned_to = form.assigned_to.data or None
        task.project_id = form.project_id.data or None
        task.tags = form.tags.data
        task.is_recurring = form.is_recurring.data
        task.recurrence_rule = form.recurrence_rule.data
        db.session.commit()
        flash('Task updated.', 'success')
        return redirect(url_for('tasks.task_detail', tenant_slug=tenant_slug, task_id=task.id))
    return render_template('tasks/task_form.html', form=form, title='Edit Task',
                           task=task, tenant_slug=tenant_slug)


@tasks_bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
@module_required('tasks')
def task_delete(tenant_slug, task_id):
    from takt.app.models.tenant import Task
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.', 'success')
    return redirect(url_for('tasks.task_list', tenant_slug=tenant_slug))


@tasks_bp.route('/<int:task_id>/timer/start', methods=['POST'])
@login_required
@module_required('tasks')
def timer_start(tenant_slug, task_id):
    session['timer_task_id'] = task_id
    session['timer_start'] = datetime.utcnow().isoformat()
    flash('Timer started.', 'info')
    return redirect(url_for('tasks.task_detail', tenant_slug=tenant_slug, task_id=task_id))


@tasks_bp.route('/<int:task_id>/timer/stop', methods=['POST'])
@login_required
@module_required('tasks')
def timer_stop(tenant_slug, task_id):
    from takt.app.models.tenant import TaskTimeEntry
    start_str = session.pop('timer_start', None)
    session.pop('timer_task_id', None)
    if start_str:
        started = datetime.fromisoformat(start_str)
        ended = datetime.utcnow()
        duration = int((ended - started).total_seconds() / 60)
        if duration < 1:
            duration = 1
        entry = TaskTimeEntry(
            task_id=task_id,
            user_id=current_user.id,
            started_at=started,
            ended_at=ended,
            duration_minutes=duration,
        )
        db.session.add(entry)
        db.session.commit()
        flash(f'Timer stopped. {duration} minutes logged.', 'success')
    return redirect(url_for('tasks.task_detail', tenant_slug=tenant_slug, task_id=task_id))


@tasks_bp.route('/<int:task_id>/time', methods=['POST'])
@login_required
@module_required('tasks')
def task_log_time(tenant_slug, task_id):
    from takt.app.models.tenant import TaskTimeEntry
    Task = None  # avoid circular import warning
    from takt.app.models.tenant import Task
    task = Task.query.get_or_404(task_id)
    form = ManualTimeForm()
    if form.validate_on_submit():
        entry = TaskTimeEntry(
            task_id=task.id,
            user_id=current_user.id,
            duration_minutes=form.duration_minutes.data,
            note=form.note.data,
        )
        db.session.add(entry)
        db.session.commit()
        flash(f'{form.duration_minutes.data} minutes logged.', 'success')
    return redirect(url_for('tasks.task_detail', tenant_slug=tenant_slug, task_id=task_id))


@tasks_bp.route('/calendar')
@login_required
@module_required('tasks')
def calendar(tenant_slug):
    from takt.app.models.tenant import Task, CalendarEvent
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)

    # Build calendar grid
    _, days_in_month = cal_module.monthrange(year, month)
    first_weekday = date(year, month, 1).weekday()  # 0=Mon

    # Tasks with due_date in this month
    tasks = Task.query.filter(
        db.extract('year', Task.due_date) == year,
        db.extract('month', Task.due_date) == month,
    ).all()

    # Calendar events in this month
    month_start = datetime(year, month, 1)
    if month == 12:
        month_end = datetime(year + 1, 1, 1)
    else:
        month_end = datetime(year, month + 1, 1)
    events = CalendarEvent.query.filter(
        CalendarEvent.start_datetime >= month_start,
        CalendarEvent.start_datetime < month_end,
    ).all()

    # Group by day
    tasks_by_day = {}
    for task in tasks:
        d = task.due_date.day
        tasks_by_day.setdefault(d, []).append(task)
    events_by_day = {}
    for ev in events:
        d = ev.start_datetime.day
        events_by_day.setdefault(d, []).append(ev)

    # Prev/next
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return render_template('tasks/calendar.html',
                           year=year, month=month,
                           days_in_month=days_in_month,
                           first_weekday=first_weekday,
                           tasks_by_day=tasks_by_day,
                           events_by_day=events_by_day,
                           prev_month=prev_month, prev_year=prev_year,
                           next_month=next_month, next_year=next_year,
                           month_name=cal_module.month_name[month],
                           today=date.today(),
                           tenant_slug=tenant_slug)
