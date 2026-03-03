from app import app, db
from models import User

def create_admin():
    with app.app_context():
        email = "admin@bakkour.com"
        password = "Admin123!"

        existing = User.query.filter_by(email=email).first()
        if existing:
            print("Admin already exists.")
            return

        admin = User(
            email=email,
            role="admin",
            status="active",
        )
        admin.set_password(password)

        db.session.add(admin)
        db.session.commit()

        print("Admin created successfully!")

if __name__ == "__main__":
    create_admin()