from decimal import Decimal
from datetime import date
from flask import render_template, redirect, url_for, flash, request, g
from flask_login import login_required
from takt.app.blueprints.billing import billing_bp
from takt.app.blueprints.billing.forms import (
    CustomerForm, CustomerSubscriptionForm, CustomerInvoiceForm
)
from takt.app.extensions import db
from takt.app.middleware.module_guard import module_required


# ── Dashboard ─────────────────────────────────────────────────────────────────

@billing_bp.route('/')
@login_required
@module_required('billing')
def dashboard(tenant_slug):
    from takt.app.models.tenant import Customer, CustomerSubscription, CustomerInvoice
    total_customers = Customer.query.count()
    active_subs = CustomerSubscription.query.filter_by(status='active').all()
    mrr = sum(
        float(s.price) if s.billing_cycle == 'monthly'
        else float(s.price) / 12
        for s in active_subs
    )
    outstanding = CustomerInvoice.query.filter(
        CustomerInvoice.status.in_(['sent', 'overdue'])
    ).all()
    outstanding_amount = sum(float(i.amount) for i in outstanding)
    overdue_count = CustomerInvoice.query.filter_by(status='overdue').count()
    recent_invoices = CustomerInvoice.query.order_by(
        CustomerInvoice.issued_date.desc()
    ).limit(5).all()
    return render_template('billing/dashboard.html',
                           total_customers=total_customers,
                           mrr=round(mrr, 2),
                           outstanding_amount=round(outstanding_amount, 2),
                           overdue_count=overdue_count,
                           recent_invoices=recent_invoices,
                           tenant_slug=tenant_slug)


# ── Customers ─────────────────────────────────────────────────────────────────

@billing_bp.route('/customers')
@login_required
@module_required('billing')
def customers(tenant_slug):
    from takt.app.models.tenant import Customer
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    query = Customer.query
    if q:
        query = query.filter(
            db.or_(Customer.name.ilike(f'%{q}%'), Customer.email.ilike(f'%{q}%'))
        )
    customers = query.order_by(Customer.name).paginate(page=page, per_page=25, error_out=False)
    return render_template('billing/customers.html', customers=customers, q=q, tenant_slug=tenant_slug)


@billing_bp.route('/customers/<int:customer_id>')
@login_required
@module_required('billing')
def customer_detail(tenant_slug, customer_id):
    from takt.app.models.tenant import Customer
    customer = Customer.query.get_or_404(customer_id)
    sub_form = CustomerSubscriptionForm()
    return render_template('billing/customer_detail.html', customer=customer,
                           sub_form=sub_form, tenant_slug=tenant_slug)


@billing_bp.route('/customers/new', methods=['GET', 'POST'])
@login_required
@module_required('billing')
def customer_new(tenant_slug):
    from takt.app.models.tenant import Customer
    form = CustomerForm()
    if form.validate_on_submit():
        c = Customer(
            name=form.name.data, email=form.email.data,
            phone=form.phone.data, address=form.address.data, notes=form.notes.data,
        )
        db.session.add(c)
        db.session.commit()
        flash('Customer created.', 'success')
        return redirect(url_for('billing.customer_detail', tenant_slug=tenant_slug, customer_id=c.id))
    return render_template('billing/customer_form.html', form=form, title='New Customer', tenant_slug=tenant_slug)


@billing_bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
@module_required('billing')
def customer_edit(tenant_slug, customer_id):
    from takt.app.models.tenant import Customer
    c = Customer.query.get_or_404(customer_id)
    form = CustomerForm(obj=c)
    if form.validate_on_submit():
        c.name = form.name.data; c.email = form.email.data
        c.phone = form.phone.data; c.address = form.address.data; c.notes = form.notes.data
        db.session.commit()
        flash('Customer updated.', 'success')
        return redirect(url_for('billing.customer_detail', tenant_slug=tenant_slug, customer_id=c.id))
    return render_template('billing/customer_form.html', form=form, title='Edit Customer',
                           customer=c, tenant_slug=tenant_slug)


@billing_bp.route('/customers/<int:customer_id>/delete', methods=['POST'])
@login_required
@module_required('billing')
def customer_delete(tenant_slug, customer_id):
    from takt.app.models.tenant import Customer
    c = Customer.query.get_or_404(customer_id)
    db.session.delete(c)
    db.session.commit()
    flash('Customer deleted.', 'success')
    return redirect(url_for('billing.customers', tenant_slug=tenant_slug))


# ── Subscriptions ─────────────────────────────────────────────────────────────

@billing_bp.route('/customers/<int:customer_id>/subscriptions/new', methods=['POST'])
@login_required
@module_required('billing')
def subscription_new(tenant_slug, customer_id):
    from takt.app.models.tenant import CustomerSubscription
    form = CustomerSubscriptionForm()
    if form.validate_on_submit():
        sub = CustomerSubscription(
            customer_id=customer_id,
            plan_name=form.plan_name.data,
            price=form.price.data,
            billing_cycle=form.billing_cycle.data,
            start_date=form.start_date.data,
            status=form.status.data,
        )
        db.session.add(sub)
        db.session.commit()
        flash('Subscription created.', 'success')
    return redirect(url_for('billing.customer_detail', tenant_slug=tenant_slug, customer_id=customer_id))


@billing_bp.route('/subscriptions/<int:sub_id>/cancel', methods=['POST'])
@login_required
@module_required('billing')
def subscription_cancel(tenant_slug, sub_id):
    from takt.app.models.tenant import CustomerSubscription
    sub = CustomerSubscription.query.get_or_404(sub_id)
    sub.status = 'cancelled'
    db.session.commit()
    flash('Subscription cancelled.', 'warning')
    return redirect(url_for('billing.customer_detail', tenant_slug=tenant_slug, customer_id=sub.customer_id))


# ── Invoices ──────────────────────────────────────────────────────────────────

@billing_bp.route('/invoices')
@login_required
@module_required('billing')
def invoices(tenant_slug):
    from takt.app.models.tenant import CustomerInvoice, Customer
    status = request.args.get('status', '')
    customer_id = request.args.get('customer_id', '')
    page = request.args.get('page', 1, type=int)
    q = CustomerInvoice.query
    if status:
        q = q.filter(CustomerInvoice.status == status)
    if customer_id:
        q = q.filter(CustomerInvoice.customer_id == int(customer_id))
    invoices = q.order_by(CustomerInvoice.issued_date.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    customers = Customer.query.order_by(Customer.name).all()
    return render_template('billing/invoices.html', invoices=invoices, customers=customers,
                           status=status, customer_id=customer_id, tenant_slug=tenant_slug)


@billing_bp.route('/invoices/<int:invoice_id>')
@login_required
@module_required('billing')
def invoice_detail(tenant_slug, invoice_id):
    from takt.app.models.tenant import CustomerInvoice
    inv = CustomerInvoice.query.get_or_404(invoice_id)
    return render_template('billing/invoice_detail.html', inv=inv, tenant_slug=tenant_slug)


@billing_bp.route('/invoices/new', methods=['GET', 'POST'])
@login_required
@module_required('billing')
def invoice_new(tenant_slug):
    from takt.app.models.tenant import CustomerInvoice, CustomerInvoiceLineItem
    form = CustomerInvoiceForm()
    if form.validate_on_submit():
        inv = CustomerInvoice(
            customer_id=form.customer_id.data,
            status=form.status.data,
            issued_date=form.issued_date.data,
            due_date=form.due_date.data,
            paid_date=form.paid_date.data,
            amount=Decimal('0'),
        )
        db.session.add(inv)
        db.session.flush()

        total = Decimal('0')
        descs = request.form.getlist('item_desc')
        qtys = request.form.getlist('item_qty')
        prices = request.form.getlist('item_price')
        for desc, qty, price in zip(descs, qtys, prices):
            try:
                q = Decimal(qty)
                p = Decimal(price)
                line_total = q * p
                total += line_total
                db.session.add(CustomerInvoiceLineItem(
                    invoice_id=inv.id,
                    description=desc,
                    quantity=q,
                    unit_price=p,
                    total=line_total,
                ))
            except Exception:
                pass
        inv.amount = total
        db.session.commit()
        flash('Invoice created.', 'success')
        return redirect(url_for('billing.invoice_detail', tenant_slug=tenant_slug, invoice_id=inv.id))
    return render_template('billing/invoice_form.html', form=form, title='New Invoice', tenant_slug=tenant_slug)


@billing_bp.route('/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
@module_required('billing')
def invoice_edit(tenant_slug, invoice_id):
    from takt.app.models.tenant import CustomerInvoice, CustomerInvoiceLineItem
    inv = CustomerInvoice.query.get_or_404(invoice_id)
    form = CustomerInvoiceForm(obj=inv)
    if form.validate_on_submit():
        inv.customer_id = form.customer_id.data
        inv.status = form.status.data
        inv.issued_date = form.issued_date.data
        inv.due_date = form.due_date.data
        inv.paid_date = form.paid_date.data

        # Rebuild line items
        CustomerInvoiceLineItem.query.filter_by(invoice_id=inv.id).delete()
        total = Decimal('0')
        descs = request.form.getlist('item_desc')
        qtys = request.form.getlist('item_qty')
        prices = request.form.getlist('item_price')
        for desc, qty, price in zip(descs, qtys, prices):
            try:
                q = Decimal(qty)
                p = Decimal(price)
                line_total = q * p
                total += line_total
                db.session.add(CustomerInvoiceLineItem(
                    invoice_id=inv.id, description=desc,
                    quantity=q, unit_price=p, total=line_total,
                ))
            except Exception:
                pass
        inv.amount = total
        db.session.commit()
        flash('Invoice updated.', 'success')
        return redirect(url_for('billing.invoice_detail', tenant_slug=tenant_slug, invoice_id=inv.id))
    return render_template('billing/invoice_form.html', form=form, title='Edit Invoice',
                           inv=inv, tenant_slug=tenant_slug)


@billing_bp.route('/invoices/<int:invoice_id>/delete', methods=['POST'])
@login_required
@module_required('billing')
def invoice_delete(tenant_slug, invoice_id):
    from takt.app.models.tenant import CustomerInvoice
    inv = CustomerInvoice.query.get_or_404(invoice_id)
    db.session.delete(inv)
    db.session.commit()
    flash('Invoice deleted.', 'success')
    return redirect(url_for('billing.invoices', tenant_slug=tenant_slug))
