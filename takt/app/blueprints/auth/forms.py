from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember me')
    submit = SubmitField('Sign in')


class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Optional(), Length(6, 128)])
    confirm = PasswordField('Confirm password', validators=[EqualTo('password')])
    role = SelectField('Role', choices=[('user', 'User'), ('admin', 'Admin')])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')


class SiteForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 120)])
    address = StringField('Address', validators=[Optional()])
    contact_email = StringField('Contact email', validators=[Optional(), Email()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')
