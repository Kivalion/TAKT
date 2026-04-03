from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional, Email, Length


class ContactForm(FlaskForm):
    first_name = StringField('First name', validators=[DataRequired(), Length(1, 80)])
    last_name = StringField('Last name', validators=[DataRequired(), Length(1, 80)])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(0, 40)])
    company = StringField('Company', validators=[Optional(), Length(0, 120)])
    site_id = SelectField('Site', coerce=int, validators=[Optional()])
    notes = TextAreaField('Notes (Markdown)', validators=[Optional()])
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from takt.app.models.tenant import Site
        sites = Site.query.filter_by(is_active=True).order_by(Site.name).all()
        self.site_id.choices = [(0, '— None —')] + [(s.id, s.name) for s in sites]
