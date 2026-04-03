from flask import render_template, redirect, url_for, flash, request, g
from flask_login import login_required, current_user
from takt.app.blueprints.crm import crm_bp
from takt.app.blueprints.crm.forms import ContactForm
from takt.app.extensions import db
from takt.app.middleware.module_guard import module_required


@crm_bp.route('/')
@login_required
@module_required('crm')
def contacts(tenant_slug):
    from takt.app.models.tenant import Contact, Site
    q = request.args.get('q', '').strip()
    site_id = request.args.get('site_id', '', type=str)
    page = request.args.get('page', 1, type=int)

    query = Contact.query
    if q:
        like = f'%{q}%'
        query = query.filter(
            db.or_(
                Contact.first_name.ilike(like),
                Contact.last_name.ilike(like),
                Contact.email.ilike(like),
                Contact.company.ilike(like),
            )
        )
    if site_id:
        query = query.filter(Contact.site_id == int(site_id))

    contacts = query.order_by(Contact.last_name, Contact.first_name).paginate(
        page=page, per_page=25, error_out=False
    )
    sites = Site.query.filter_by(is_active=True).order_by(Site.name).all()
    return render_template('crm/contacts.html', contacts=contacts, sites=sites,
                           q=q, site_id=site_id, tenant_slug=tenant_slug)


@crm_bp.route('/<int:contact_id>')
@login_required
@module_required('crm')
def contact_detail(tenant_slug, contact_id):
    from takt.app.models.tenant import Contact
    import markdown
    contact = Contact.query.get_or_404(contact_id)
    notes_html = markdown.markdown(contact.notes or '', extensions=['nl2br']) if contact.notes else ''
    return render_template('crm/contact_detail.html', contact=contact,
                           notes_html=notes_html, tenant_slug=tenant_slug)


@crm_bp.route('/new', methods=['GET', 'POST'])
@login_required
@module_required('crm')
def contact_new(tenant_slug):
    from takt.app.models.tenant import Contact
    form = ContactForm()
    if form.validate_on_submit():
        contact = Contact(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            company=form.company.data,
            site_id=form.site_id.data or None,
            notes=form.notes.data,
            created_by=current_user.id,
        )
        db.session.add(contact)
        db.session.commit()
        flash('Contact created.', 'success')
        return redirect(url_for('crm.contact_detail', tenant_slug=tenant_slug, contact_id=contact.id))
    return render_template('crm/contact_form.html', form=form, title='New Contact', tenant_slug=tenant_slug)


@crm_bp.route('/<int:contact_id>/edit', methods=['GET', 'POST'])
@login_required
@module_required('crm')
def contact_edit(tenant_slug, contact_id):
    from takt.app.models.tenant import Contact
    contact = Contact.query.get_or_404(contact_id)
    form = ContactForm(obj=contact)
    if form.validate_on_submit():
        contact.first_name = form.first_name.data
        contact.last_name = form.last_name.data
        contact.email = form.email.data
        contact.phone = form.phone.data
        contact.company = form.company.data
        contact.site_id = form.site_id.data or None
        contact.notes = form.notes.data
        db.session.commit()
        flash('Contact updated.', 'success')
        return redirect(url_for('crm.contact_detail', tenant_slug=tenant_slug, contact_id=contact.id))
    return render_template('crm/contact_form.html', form=form, title='Edit Contact',
                           contact=contact, tenant_slug=tenant_slug)


@crm_bp.route('/<int:contact_id>/delete', methods=['POST'])
@login_required
@module_required('crm')
def contact_delete(tenant_slug, contact_id):
    from takt.app.models.tenant import Contact
    contact = Contact.query.get_or_404(contact_id)
    db.session.delete(contact)
    db.session.commit()
    flash('Contact deleted.', 'success')
    return redirect(url_for('crm.contacts', tenant_slug=tenant_slug))
