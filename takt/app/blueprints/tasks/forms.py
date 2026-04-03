from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, IntegerField,
    BooleanField, DateField, SubmitField
)
from wtforms.validators import DataRequired, Optional, Length, NumberRange
from datetime import datetime


class TaskForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(1, 200)])
    description = TextAreaField('Description', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('todo', 'To Do'), ('in-progress', 'In Progress'),
        ('on-hold', 'On Hold'), ('done', 'Done'),
    ])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ])
    due_date = DateField('Due date', validators=[Optional()])
    estimated_minutes = IntegerField('Estimated minutes', validators=[Optional(), NumberRange(min=0)])
    assigned_to = SelectField('Assignee', coerce=int, validators=[Optional()])
    project_id = SelectField('Project', coerce=int, validators=[Optional()])
    tags = StringField('Tags (comma-separated)', validators=[Optional(), Length(0, 255)])
    is_recurring = BooleanField('Recurring')
    recurrence_rule = StringField('Recurrence rule', validators=[Optional(), Length(0, 100)])
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from takt.app.models.tenant import User, Project
        users = User.query.filter_by(is_active=True).order_by(User.username).all()
        self.assigned_to.choices = [(0, '— Unassigned —')] + [(u.id, u.username) for u in users]
        projects = Project.query.filter(Project.status != 'completed').order_by(Project.name).all()
        self.project_id.choices = [(0, '— None —')] + [(p.id, p.name) for p in projects]


class ManualTimeForm(FlaskForm):
    duration_minutes = IntegerField('Duration (minutes)', validators=[DataRequired(), NumberRange(min=1)])
    note = StringField('Note', validators=[Optional(), Length(0, 255)])
    submit = SubmitField('Log time')


class CalendarEventForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(1, 200)])
    description = TextAreaField('Description', validators=[Optional()])
    start_datetime = StringField('Start', validators=[DataRequired()])
    end_datetime = StringField('End', validators=[DataRequired()])
    linked_task_id = SelectField('Linked task', coerce=int, validators=[Optional()])
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from takt.app.models.tenant import Task
        tasks = Task.query.filter(Task.status != 'done').order_by(Task.title).all()
        self.linked_task_id.choices = [(0, '— None —')] + [(t.id, t.title) for t in tasks]
