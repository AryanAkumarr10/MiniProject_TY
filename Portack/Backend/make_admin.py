from app import app
from models import db, User

with app.app_context():
    user = User.query.filter_by(email="aryananandkumar2@gamil.com").first()
    if not user:
        print("No user found with that email.")
    else:
        user.role = "admin"
        db.session.commit()
        print("Updated:", user.to_dict())