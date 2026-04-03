from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional, Length


class DeviceForm(FlaskForm):
    hostname = StringField('Hostname', validators=[DataRequired(), Length(1, 120)])
    serial_number = StringField('Serial number', validators=[Optional(), Length(0, 120)])
    manufacturer = StringField('Manufacturer', validators=[Optional(), Length(0, 120)])
    model = StringField('Model', validators=[Optional(), Length(0, 120)])
    device_type = SelectField('Type', choices=[
        ('workstation', 'Workstation'), ('server', 'Server'),
        ('network', 'Network'), ('printer', 'Printer'), ('other', 'Other'),
    ])
    os = StringField('OS', validators=[Optional(), Length(0, 80)])
    os_version = StringField('OS version', validators=[Optional(), Length(0, 80)])
    site_id = SelectField('Site', coerce=int, validators=[Optional()])
    assigned_to = SelectField('Assigned to', coerce=int, validators=[Optional()])
    status = SelectField('Status', choices=[
        ('active', 'Active'), ('inactive', 'Inactive'), ('decommissioned', 'Decommissioned'),
    ])
    notes = TextAreaField('Notes', validators=[Optional()])
    tags = StringField('Tags (comma-separated)', validators=[Optional()])
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from takt.app.models.tenant import Site, User
        sites = Site.query.filter_by(is_active=True).order_by(Site.name).all()
        self.site_id.choices = [(0, '— None —')] + [(s.id, s.name) for s in sites]
        users = User.query.filter_by(is_active=True).order_by(User.username).all()
        self.assigned_to.choices = [(0, '— Unassigned —')] + [(u.id, u.username) for u in users]
