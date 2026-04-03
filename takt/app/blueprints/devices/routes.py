from flask import render_template, redirect, url_for, flash, request, g
from flask_login import login_required, current_user
from takt.app.blueprints.devices import devices_bp
from takt.app.blueprints.devices.forms import DeviceForm
from takt.app.extensions import db
from takt.app.middleware.module_guard import module_required


@devices_bp.route('/')
@login_required
@module_required('devices')
def device_list(tenant_slug):
    from takt.app.models.tenant import Device, Site
    q = request.args.get('q', '').strip()
    site_id = request.args.get('site_id', '')
    device_type = request.args.get('type', '')
    status = request.args.get('status', '')
    tag = request.args.get('tag', '')
    page = request.args.get('page', 1, type=int)

    query = Device.query
    if q:
        like = f'%{q}%'
        query = query.filter(
            db.or_(
                Device.hostname.ilike(like),
                Device.serial_number.ilike(like),
                Device.model.ilike(like),
            )
        )
    if site_id:
        query = query.filter(Device.site_id == int(site_id))
    if device_type:
        query = query.filter(Device.device_type == device_type)
    if status:
        query = query.filter(Device.status == status)
    if tag:
        from takt.app.models.tenant import DeviceTag
        device_ids = [dt.device_id for dt in DeviceTag.query.filter(
            DeviceTag.tag.ilike(f'%{tag}%')
        ).all()]
        query = query.filter(Device.id.in_(device_ids))

    devices = query.order_by(Device.hostname).paginate(page=page, per_page=25, error_out=False)
    sites = Site.query.filter_by(is_active=True).order_by(Site.name).all()
    return render_template('devices/device_list.html', devices=devices, sites=sites,
                           q=q, site_id=site_id, device_type=device_type,
                           status=status, tag=tag, tenant_slug=tenant_slug)


@devices_bp.route('/<int:device_id>')
@login_required
@module_required('devices')
def device_detail(tenant_slug, device_id):
    from takt.app.models.tenant import Device
    device = Device.query.get_or_404(device_id)
    return render_template('devices/device_detail.html', device=device, tenant_slug=tenant_slug)


@devices_bp.route('/new', methods=['GET', 'POST'])
@login_required
@module_required('devices')
def device_new(tenant_slug):
    from takt.app.models.tenant import Device, DeviceTag
    form = DeviceForm()
    if form.validate_on_submit():
        device = Device(
            hostname=form.hostname.data,
            serial_number=form.serial_number.data,
            manufacturer=form.manufacturer.data,
            model=form.model.data,
            device_type=form.device_type.data,
            os=form.os.data,
            os_version=form.os_version.data,
            site_id=form.site_id.data or None,
            assigned_to=form.assigned_to.data or None,
            status=form.status.data,
            notes=form.notes.data,
            registered_by=current_user.id,
        )
        db.session.add(device)
        db.session.flush()

        # Save tags
        for tag in (form.tags.data or '').split(','):
            tag = tag.strip()
            if tag:
                db.session.add(DeviceTag(device_id=device.id, tag=tag))

        db.session.commit()
        flash('Device registered.', 'success')
        return redirect(url_for('devices.device_detail', tenant_slug=tenant_slug, device_id=device.id))
    return render_template('devices/device_form.html', form=form, title='Register Device', tenant_slug=tenant_slug)


@devices_bp.route('/<int:device_id>/edit', methods=['GET', 'POST'])
@login_required
@module_required('devices')
def device_edit(tenant_slug, device_id):
    from takt.app.models.tenant import Device, DeviceTag
    device = Device.query.get_or_404(device_id)
    existing_tags = ', '.join(t.tag for t in device.tags)
    form = DeviceForm(obj=device)
    if request.method == 'GET':
        form.tags.data = existing_tags

    if form.validate_on_submit():
        device.hostname = form.hostname.data
        device.serial_number = form.serial_number.data
        device.manufacturer = form.manufacturer.data
        device.model = form.model.data
        device.device_type = form.device_type.data
        device.os = form.os.data
        device.os_version = form.os_version.data
        device.site_id = form.site_id.data or None
        device.assigned_to = form.assigned_to.data or None
        device.status = form.status.data
        device.notes = form.notes.data

        # Update tags
        DeviceTag.query.filter_by(device_id=device.id).delete()
        for tag in (form.tags.data or '').split(','):
            tag = tag.strip()
            if tag:
                db.session.add(DeviceTag(device_id=device.id, tag=tag))

        db.session.commit()
        flash('Device updated.', 'success')
        return redirect(url_for('devices.device_detail', tenant_slug=tenant_slug, device_id=device.id))
    return render_template('devices/device_form.html', form=form, title='Edit Device',
                           device=device, tenant_slug=tenant_slug)


@devices_bp.route('/<int:device_id>/decommission', methods=['POST'])
@login_required
@module_required('devices')
def device_decommission(tenant_slug, device_id):
    from takt.app.models.tenant import Device
    device = Device.query.get_or_404(device_id)
    device.status = 'decommissioned'
    db.session.commit()
    flash(f'Device {device.hostname} decommissioned.', 'warning')
    return redirect(url_for('devices.device_detail', tenant_slug=tenant_slug, device_id=device_id))


@devices_bp.route('/<int:device_id>/delete', methods=['POST'])
@login_required
@module_required('devices')
def device_delete(tenant_slug, device_id):
    from takt.app.models.tenant import Device
    device = Device.query.get_or_404(device_id)
    db.session.delete(device)
    db.session.commit()
    flash('Device deleted.', 'success')
    return redirect(url_for('devices.device_list', tenant_slug=tenant_slug))
