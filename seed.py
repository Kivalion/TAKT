"""
Seed script for TAKT.
Creates super admin, demo tenant, sample data.
"""
import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

# Ensure we can import the app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from takt.app import create_app
from takt.app.extensions import db
from sqlalchemy import text

app = create_app()

ALL_MODULES = ['crm', 'ticketing', 'tasks', 'projects', 'devices', 'billing']
TENANT_SLUG = 'demo'
TENANT_SCHEMA = f'tenant_{TENANT_SLUG}'


def reset_search_path_public():
    db.session.execute(text('SET search_path TO public'))


def reset_search_path_tenant():
    db.session.execute(text(f'SET search_path TO {TENANT_SCHEMA}, public'))


def create_public_schema():
    """Create only public schema tables (not tenant tables)."""
    reset_search_path_public()
    from takt.app.models.public import (
        Tenant, TenantModule, SuperAdminUser, ImpersonationLog,
        BillingPlan, TenantSubscription, Invoice, InvoiceLineItem
    )
    public_tables = [t for t in db.metadata.sorted_tables if t.schema == 'public']
    with db.engine.connect() as conn:
        for table in public_tables:
            table.create(conn, checkfirst=True)
        conn.commit()
    print("✓ Public schema tables created")


def create_tenant_schema(slug):
    """Create a tenant schema and its tables."""
    from sqlalchemy import MetaData
    # Import all tenant models so their tables are registered in db.metadata
    from takt.app.models.tenant import (
        User, Site, UserSite, Contact, Ticket, TicketComment, TimeEntry,
        Task, TaskTimeEntry, CalendarEvent, Project, ProjectMember,
        Device, DeviceTag, Customer, CustomerSubscription,
        CustomerInvoice, CustomerInvoiceLineItem,
    )

    schema_name = f'tenant_{slug}'
    tenant_tables = [t for t in db.metadata.sorted_tables if t.schema is None]

    # Clone ALL tables into a single new MetaData before creating anything.
    # This lets SQLAlchemy resolve FK references between tenant tables
    # (e.g. contacts.site_id → tenant_demo.sites) correctly.
    new_meta = MetaData()
    for table in tenant_tables:
        table.to_metadata(new_meta, schema=schema_name)

    with db.engine.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        new_meta.create_all(conn, checkfirst=True)
        conn.commit()

    print(f"✓ Tenant schema '{schema_name}' created")


def seed_super_admin():
    from takt.app.models.public import SuperAdminUser
    reset_search_path_public()
    existing = SuperAdminUser.query.filter_by(username='admin').first()
    if existing:
        print("  Super admin already exists, skipping")
        return existing
    admin = SuperAdminUser(username='admin', email='admin@takt.local')
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    print("✓ Super admin created: admin / admin123")
    return admin


def seed_tenant():
    from takt.app.models.public import Tenant, TenantModule
    reset_search_path_public()
    existing = Tenant.query.filter_by(slug=TENANT_SLUG).first()
    if existing:
        print("  Demo tenant already exists, skipping")
        return existing
    tenant = Tenant(name='Demo BV', slug=TENANT_SLUG, is_active=True)
    db.session.add(tenant)
    db.session.flush()

    for mod in ALL_MODULES:
        db.session.add(TenantModule(tenant_id=tenant.id, module_name=mod, is_enabled=True))

    db.session.commit()
    print(f"✓ Demo tenant created: {TENANT_SLUG}")
    return tenant


def seed_billing_plan(tenant):
    from takt.app.models.public import BillingPlan, TenantSubscription, Invoice, InvoiceLineItem
    reset_search_path_public()
    plan = BillingPlan.query.filter_by(name='Standard MSP').first()
    if not plan:
        plan = BillingPlan(
            name='Standard MSP',
            description='Full MSP platform access',
            price_monthly=Decimal('99.00'),
            price_yearly=Decimal('990.00'),
        )
        db.session.add(plan)
        db.session.flush()
        print("✓ Billing plan created")

    sub = TenantSubscription.query.filter_by(tenant_id=tenant.id).first()
    if not sub:
        sub = TenantSubscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            start_date=date.today() - timedelta(days=30),
            status='active',
            billing_cycle='monthly',
        )
        db.session.add(sub)
        print("✓ Tenant subscription created")

    # Two sample MSP invoices
    if Invoice.query.filter_by(tenant_id=tenant.id).count() == 0:
        # Paid invoice
        inv1 = Invoice(
            tenant_id=tenant.id,
            amount=Decimal('99.00'),
            status='paid',
            issued_date=date.today() - timedelta(days=60),
            due_date=date.today() - timedelta(days=30),
            paid_date=date.today() - timedelta(days=28),
            notes='Monthly fee — February',
        )
        db.session.add(inv1)
        db.session.flush()
        db.session.add(InvoiceLineItem(
            invoice_id=inv1.id,
            description='Standard MSP — Monthly',
            quantity=Decimal('1'),
            unit_price=Decimal('99.00'),
            total=Decimal('99.00'),
        ))

        # Outstanding invoice
        inv2 = Invoice(
            tenant_id=tenant.id,
            amount=Decimal('99.00'),
            status='sent',
            issued_date=date.today() - timedelta(days=5),
            due_date=date.today() + timedelta(days=25),
            notes='Monthly fee — current',
        )
        db.session.add(inv2)
        db.session.flush()
        db.session.add(InvoiceLineItem(
            invoice_id=inv2.id,
            description='Standard MSP — Monthly',
            quantity=Decimal('1'),
            unit_price=Decimal('99.00'),
            total=Decimal('99.00'),
        ))
        print("✓ MSP invoices created (1 paid, 1 outstanding)")

    db.session.commit()


def seed_tenant_data():
    from takt.app.models.tenant import (
        User, Site, Contact, Ticket, TicketComment, TimeEntry,
        Task, TaskTimeEntry, Project, ProjectMember,
        Device, DeviceTag, Customer, CustomerSubscription,
        CustomerInvoice, CustomerInvoiceLineItem,
    )
    reset_search_path_tenant()

    # ── Users ──────────────────────────────────────────────────────────────────
    admin_user = User.query.filter_by(username='demo_admin').first()
    if not admin_user:
        admin_user = User(username='demo_admin', email='admin@demo.local', role='admin')
        admin_user.set_password('demo123')
        admin_user._tenant_slug = TENANT_SLUG
        db.session.add(admin_user)

    user1 = User.query.filter_by(username='alice').first()
    if not user1:
        user1 = User(username='alice', email='alice@demo.local', role='user')
        user1.set_password('demo123')
        user1._tenant_slug = TENANT_SLUG
        db.session.add(user1)

    user2 = User.query.filter_by(username='bob').first()
    if not user2:
        user2 = User(username='bob', email='bob@demo.local', role='user')
        user2.set_password('demo123')
        user2._tenant_slug = TENANT_SLUG
        db.session.add(user2)

    db.session.flush()
    print("✓ Tenant users created: demo_admin, alice, bob (all pw: demo123)")

    # ── Sites ──────────────────────────────────────────────────────────────────
    site1 = Site.query.filter_by(name='HQ Amsterdam').first()
    if not site1:
        site1 = Site(name='HQ Amsterdam', address='Herengracht 1, Amsterdam', contact_email='hq@demo.local')
        db.session.add(site1)

    site2 = Site.query.filter_by(name='Rotterdam Branch').first()
    if not site2:
        site2 = Site(name='Rotterdam Branch', address='Coolsingel 42, Rotterdam', contact_email='rtd@demo.local')
        db.session.add(site2)

    db.session.flush()
    print("✓ Sites created")

    # ── CRM Contacts ───────────────────────────────────────────────────────────
    if Contact.query.count() == 0:
        contacts_data = [
            ('Jan', 'de Vries', 'jan@example.com', '+31612345678', 'ACME Corp', site1.id),
            ('Maria', 'Jansen', 'maria@techco.nl', '+31687654321', 'TechCo', site1.id),
            ('Pieter', 'Bakker', 'pieter@bakker.nl', '+31698765432', 'Bakker BV', site2.id),
            ('Sophie', 'Visser', 'sophie@visser.com', None, 'Visser & Zn', site2.id),
            ('Thomas', 'Meijer', 'thomas@meijer.nl', '+31655544433', 'Meijer IT', None),
            ('Laura', 'van den Berg', 'laura@example.com', None, 'ACME Corp', site1.id),
        ]
        for first, last, email, phone, company, sid in contacts_data:
            db.session.add(Contact(
                first_name=first, last_name=last,
                email=email, phone=phone, company=company,
                site_id=sid, created_by=admin_user.id,
                notes=f'Sample contact for {company}. **Status**: Active.',
            ))
        print("✓ CRM contacts seeded")

    # ── Project ────────────────────────────────────────────────────────────────
    project = Project.query.filter_by(name='Network Overhaul').first()
    if not project:
        project = Project(
            name='Network Overhaul',
            description='Full network infrastructure replacement at HQ',
            status='active',
            start_date=date.today() - timedelta(days=14),
            end_date=date.today() + timedelta(days=60),
            site_id=site1.id,
            manager_id=admin_user.id,
        )
        db.session.add(project)
        db.session.flush()
        db.session.add(ProjectMember(project_id=project.id, user_id=user1.id, role='member'))
        db.session.add(ProjectMember(project_id=project.id, user_id=user2.id, role='member'))
        print("✓ Project created")

    db.session.flush()

    # ── Tickets ────────────────────────────────────────────────────────────────
    if Ticket.query.count() == 0:
        tickets_data = [
            ('Server not responding', 'The main file server at HQ is down since 9am.', 'open', 'critical', 'incident', admin_user.id, site1.id),
            ('VPN setup for remote workers', 'Need to configure VPN for 10 new employees.', 'in-progress', 'high', 'request', user1.id, site1.id),
            ('Office printer offline', 'HP LaserJet on 2nd floor is not reachable.', 'on-hold', 'low', 'incident', user2.id, site2.id),
            ('Switch firmware update', 'Schedule firmware update for all managed switches.', 'open', 'medium', 'change', admin_user.id, site1.id),
            ('Email migration planning', 'Plan the migration from on-prem Exchange to M365.', 'open', 'high', 'request', user1.id, site2.id),
            ('New workstation setup', 'Set up new Dell workstation for new hire.', 'resolved', 'medium', 'request', user2.id, site1.id),
        ]
        ticket_objs = []
        for title, desc, status, prio, ttype, assigned, sid in tickets_data:
            t = Ticket(
                title=title, description=desc,
                status=status, priority=prio, type=ttype,
                assigned_to=assigned, site_id=sid,
                project_id=project.id if 'Switch' in title or 'VPN' in title else None,
                created_by=admin_user.id,
            )
            db.session.add(t)
            ticket_objs.append(t)
        db.session.flush()

        # Comments and time entries
        for i, t in enumerate(ticket_objs[:3]):
            db.session.add(TicketComment(
                ticket_id=t.id, user_id=admin_user.id,
                body=f'Initial assessment done. Will follow up shortly.',
            ))
            db.session.add(TimeEntry(
                ticket_id=t.id, user_id=user1.id,
                minutes=30 + i * 15,
                note='Investigation',
            ))
        print("✓ Tickets seeded")

    # ── Tasks ──────────────────────────────────────────────────────────────────
    if Task.query.count() == 0:
        today = date.today()
        tasks_data = [
            ('Review network diagram', 'Review the current topology doc', 'todo', 'high', today + timedelta(days=1), admin_user.id),
            ('Order replacement switches', 'Order 3x Cisco C9200 switches', 'in-progress', 'high', today + timedelta(days=3), user1.id),
            ('Update asset inventory', 'Ensure all devices are in the register', 'todo', 'medium', today + timedelta(days=7), user2.id),
            ('Weekly status report', 'Send weekly update to management', 'todo', 'low', today, admin_user.id),
            ('Patch Tuesday', 'Apply patches to all servers', 'todo', 'high', today + timedelta(days=2), user1.id),
            ('Test backup restore', 'Verify backup integrity on test server', 'done', 'medium', today - timedelta(days=2), user2.id),
        ]
        for title, desc, status, prio, due, assignee in tasks_data:
            t = Task(
                title=title, description=desc, status=status, priority=prio,
                due_date=due, assigned_to=assignee,
                project_id=project.id,
                created_by=admin_user.id,
                tags='msp,infrastructure' if 'switch' in title.lower() or 'network' in title.lower() else 'operations',
                estimated_minutes=60,
            )
            db.session.add(t)
        db.session.flush()
        print("✓ Tasks seeded")

    # ── Devices ────────────────────────────────────────────────────────────────
    if Device.query.count() == 0:
        devices_data = [
            ('srv-hq-01', 'SRV-001', 'Dell', 'PowerEdge R740', 'server', 'Ubuntu', '22.04', site1.id),
            ('ws-alice-01', 'WS-101', 'HP', 'EliteBook 840', 'workstation', 'Windows', '11', site1.id),
            ('ws-bob-01', 'WS-102', 'Lenovo', 'ThinkPad X1', 'workstation', 'Windows', '11', site2.id),
            ('sw-hq-core', 'SW-001', 'Cisco', 'C9200-24P', 'network', None, None, site1.id),
            ('prn-floor2', 'PRN-001', 'HP', 'LaserJet Pro', 'printer', None, None, site2.id),
            ('srv-backup-01', 'SRV-002', 'Dell', 'PowerEdge R540', 'server', 'Windows Server', '2022', site1.id),
        ]
        for hostname, serial, mfr, model, dtype, os, osv, sid in devices_data:
            d = Device(
                hostname=hostname, serial_number=serial,
                manufacturer=mfr, model=model, device_type=dtype,
                os=os, os_version=osv, site_id=sid,
                status='active',
                registered_by=admin_user.id,
                notes=f'Managed by TAKT.',
            )
            db.session.add(d)
            db.session.flush()
            for tag in ['managed', ('server' if dtype == 'server' else dtype)]:
                db.session.add(DeviceTag(device_id=d.id, tag=tag))
        print("✓ Devices seeded")

    # ── Billing customers ──────────────────────────────────────────────────────
    if Customer.query.count() == 0:
        customers_data = [
            ('ACME Corp', 'billing@acme.com', '+31200000001', 'Herengracht 10, Amsterdam'),
            ('TechCo BV', 'finance@techco.nl', '+31200000002', 'Coolsingel 10, Rotterdam'),
            ('Bakker BV', 'admin@bakker.nl', None, 'Kalverstraat 5, Amsterdam'),
            ('Visser & Zn', 'info@visser.nl', None, None),
        ]
        cust_objs = []
        for name, email, phone, address in customers_data:
            c = Customer(name=name, email=email, phone=phone, address=address)
            db.session.add(c)
            cust_objs.append(c)
        db.session.flush()

        # Subscriptions
        for cust in cust_objs[:3]:
            db.session.add(CustomerSubscription(
                customer_id=cust.id,
                plan_name='Managed IT',
                price=Decimal('250.00'),
                billing_cycle='monthly',
                start_date=date.today() - timedelta(days=90),
                status='active',
            ))

        db.session.flush()

        # Invoices
        today = date.today()
        for i, cust in enumerate(cust_objs[:3]):
            # Paid invoice
            inv_paid = CustomerInvoice(
                customer_id=cust.id,
                amount=Decimal('250.00'),
                status='paid',
                issued_date=today - timedelta(days=60 + i * 5),
                due_date=today - timedelta(days=30),
                paid_date=today - timedelta(days=28),
            )
            db.session.add(inv_paid)
            db.session.flush()
            db.session.add(CustomerInvoiceLineItem(
                invoice_id=inv_paid.id, description='Managed IT — Monthly',
                quantity=Decimal('1'), unit_price=Decimal('250.00'), total=Decimal('250.00'),
            ))

            # Outstanding
            inv_open = CustomerInvoice(
                customer_id=cust.id,
                amount=Decimal('250.00'),
                status='sent' if i < 2 else 'overdue',
                issued_date=today - timedelta(days=5),
                due_date=today + timedelta(days=25 if i < 2 else -5),
            )
            db.session.add(inv_open)
            db.session.flush()
            db.session.add(CustomerInvoiceLineItem(
                invoice_id=inv_open.id, description='Managed IT — Monthly',
                quantity=Decimal('1'), unit_price=Decimal('250.00'), total=Decimal('250.00'),
            ))

        print("✓ Billing customers, subscriptions, invoices seeded")

    db.session.commit()
    print("✓ All tenant data committed")


def main():
    print("\n🚀 Seeding TAKT database...\n")
    with app.app_context():
        # 1. Create public schema tables
        create_public_schema()

        # 2. Super admin
        seed_super_admin()

        # 3. Demo tenant
        tenant = seed_tenant()

        # 4. MSP billing
        seed_billing_plan(tenant)

        # 5. Provision tenant schema
        create_tenant_schema(TENANT_SLUG)

        # 6. Seed tenant data
        seed_tenant_data()

    print("\n✅ Seed complete!\n")
    print("  Super admin:   http://127.0.0.1:5000/admin/login")
    print("  Credentials:   admin / admin123\n")
    print("  Tenant login:  http://127.0.0.1:5000/t/demo/login")
    print("  Credentials:   demo_admin / demo123")
    print("                 alice / demo123")
    print("                 bob / demo123\n")


if __name__ == '__main__':
    main()
