from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, IntegerField, SubmitField
)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class TicketForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(1, 200)])
    description = TextAreaField('Description', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('open', 'Open'), ('in-progress', 'In Progress'),
        ('on-hold', 'On Hold'), ('resolved', 'Resolved'), ('closed', 'Closed'),
    ])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ])
    type = SelectField('Type', choices=[
        ('incident', 'Incident'), ('request', 'Request'), ('change', 'Change'),
    ])
    assigned_to = SelectField('Assignee', coerce=int, validators=[Optional()])
    site_id = SelectField('Site', coerce=int, validators=[Optional()])
    project_id = SelectField('Project', coerce=int, validators=[Optional()])
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from takt.app.models.tenant import User, Site, Project
        users = User.query.filter_by(is_active=True).order_by(User.username).all()
        self.assigned_to.choices = [(0, '— Unassigned —')] + [(u.id, u.username) for u in users]
        sites = Site.query.filter_by(is_active=True).order_by(Site.name).all()
        self.site_id.choices = [(0, '— None —')] + [(s.id, s.name) for s in sites]
        projects = Project.query.filter(Project.status != 'completed').order_by(Project.name).all()
        self.project_id.choices = [(0, '— None —')] + [(p.id, p.name) for p in projects]


class CommentForm(FlaskForm):
    body = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('Post comment')


class TimeEntryForm(FlaskForm):
    minutes = IntegerField('Minutes', validators=[DataRequired(), NumberRange(min=1)])
    note = StringField('Note', validators=[Optional(), Length(0, 255)])
    submit = SubmitField('Log time')
