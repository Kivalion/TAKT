from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, Length


class ProjectForm(FlaskForm):
    name = StringField('Project name', validators=[DataRequired(), Length(1, 200)])
    description = TextAreaField('Description', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('active', 'Active'), ('on-hold', 'On Hold'), ('completed', 'Completed'),
    ])
    start_date = DateField('Start date', validators=[Optional()])
    end_date = DateField('End date', validators=[Optional()])
    site_id = SelectField('Site', coerce=int, validators=[Optional()])
    manager_id = SelectField('Manager', coerce=int, validators=[Optional()])
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from takt.app.models.tenant import Site, User
        sites = Site.query.filter_by(is_active=True).order_by(Site.name).all()
        self.site_id.choices = [(0, '— None —')] + [(s.id, s.name) for s in sites]
        users = User.query.filter_by(is_active=True).order_by(User.username).all()
        self.manager_id.choices = [(0, '— None —')] + [(u.id, u.username) for u in users]


class AddMemberForm(FlaskForm):
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    role = SelectField('Role', choices=[
        ('member', 'Member'), ('lead', 'Lead'), ('viewer', 'Viewer'),
    ])
    submit = SubmitField('Add member')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from takt.app.models.tenant import User
        users = User.query.filter_by(is_active=True).order_by(User.username).all()
        self.user_id.choices = [(u.id, u.username) for u in users]
