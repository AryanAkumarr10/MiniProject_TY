from app import app
from models import db, User

with app.app_context():
    users = User.query.all()
    if not users:
        print("No users in the database yet.")
    for u in users:
        print(u.to_dict())