from flask_wtf import FlaskForm
from wtforms import (
    StringField, BooleanField, SelectField, SelectMultipleField,
    DecimalField, TextAreaField, DateField, SubmitField, widgets
)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


MODULE_CHOICES = [
    ('crm', 'CRM — Contact Management'),
    ('ticketing', 'Ticketing System'),
    ('tasks', 'Tasks'),
    ('projects', 'Projects'),
    ('devices', 'Device Registration'),
    ('billing', 'Billing'),
]


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class TenantForm(FlaskForm):
    name = StringField('Tenant name', validators=[DataRequired(), Length(1, 120)])
    slug = StringField('Slug (URL identifier)', validators=[DataRequired(), Length(2, 60)])
    is_active = BooleanField('Active', default=True)
    modules = MultiCheckboxField('Enabled modules', choices=MODULE_CHOICES)
    submit = SubmitField('Save')


class BillingPlanForm(FlaskForm):
    name = StringField('Plan name', validators=[DataRequired(), Length(1, 120)])
    description = TextAreaField('Description', validators=[Optional()])
    price_monthly = DecimalField('Monthly price', validators=[DataRequired(), NumberRange(min=0)], places=2)
    price_yearly = DecimalField('Yearly price', validators=[DataRequired(), NumberRange(min=0)], places=2)
    submit = SubmitField('Save')


class TenantSubscriptionForm(FlaskForm):
    plan_id = SelectField('Plan', coerce=int, validators=[DataRequired()])
    start_date = DateField('Start date', validators=[DataRequired()])
    end_date = DateField('End date', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('active', 'Active'), ('cancelled', 'Cancelled'), ('past_due', 'Past Due')
    ])
    billing_cycle = SelectField('Billing cycle', choices=[
        ('monthly', 'Monthly'), ('yearly', 'Yearly')
    ])
    submit = SubmitField('Save')


class InvoiceForm(FlaskForm):
    tenant_id = SelectField('Tenant', coerce=int, validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)
    status = SelectField('Status', choices=[
        ('draft', 'Draft'), ('sent', 'Sent'), ('paid', 'Paid'), ('overdue', 'Overdue')
    ])
    issued_date = DateField('Issued date', validators=[DataRequired()])
    due_date = DateField('Due date', validators=[DataRequired()])
    paid_date = DateField('Paid date', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save')
