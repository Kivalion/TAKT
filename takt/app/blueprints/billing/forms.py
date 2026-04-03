from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, DecimalField,
    DateField, SubmitField, FieldList, FormField, IntegerField
)
from wtforms.validators import DataRequired, Optional, Email, Length, NumberRange


class CustomerForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 120)])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(0, 40)])
    address = TextAreaField('Address', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save')


class CustomerSubscriptionForm(FlaskForm):
    plan_name = StringField('Plan name', validators=[DataRequired(), Length(1, 120)])
    price = DecimalField('Price', validators=[DataRequired(), NumberRange(min=0)], places=2)
    billing_cycle = SelectField('Billing cycle', choices=[
        ('monthly', 'Monthly'), ('yearly', 'Yearly'),
    ])
    start_date = DateField('Start date', validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('active', 'Active'), ('paused', 'Paused'), ('cancelled', 'Cancelled'),
    ])
    submit = SubmitField('Save')


class LineItemForm(FlaskForm):
    class Meta:
        csrf = False

    description = StringField('Description', validators=[DataRequired()])
    quantity = DecimalField('Qty', default=1, places=2)
    unit_price = DecimalField('Unit price', places=2)


class CustomerInvoiceForm(FlaskForm):
    customer_id = SelectField('Customer', coerce=int, validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('draft', 'Draft'), ('sent', 'Sent'), ('paid', 'Paid'), ('overdue', 'Overdue'),
    ])
    issued_date = DateField('Issued date', validators=[DataRequired()])
    due_date = DateField('Due date', validators=[DataRequired()])
    paid_date = DateField('Paid date', validators=[Optional()])
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from takt.app.models.tenant import Customer
        customers = Customer.query.order_by(Customer.name).all()
        self.customer_id.choices = [(c.id, c.name) for c in customers]
