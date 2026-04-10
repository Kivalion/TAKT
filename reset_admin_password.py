"""
Reset the super admin password.
Run once to fix an invalid/corrupted bcrypt hash in the database.

Usage:
    python reset_admin_password.py
    python reset_admin_password.py --username admin --password newpass
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from takt.app import create_app
from takt.app.extensions import db
from takt.app.models.public import SuperAdminUser


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset super admin password")
    parser.add_argument("--username", default="admin", help="Super admin username (default: admin)")
    parser.add_argument("--password", default="admin123", help="New password (default: admin123)")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        user = SuperAdminUser.query.filter_by(username=args.username).first()
        if not user:
            print(f"ERROR: No super admin found with username '{args.username}'")
            sys.exit(1)

        user.set_password(args.password)
        db.session.commit()
        print(f"Password reset for '{args.username}'. You can now log in with the new password.")


if __name__ == "__main__":
    main()
