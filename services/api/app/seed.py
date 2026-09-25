"""Demo seed: three users (owner, member, caregiver) and one care circle for
Ahmed Al-Karim — the fictional recipient all sample documents refer to.
Passwords are all `demo1234`."""
from .db import SessionLocal
from .models import CareCircle, Membership, Task, User, now
from .security import hash_password

DEMO_PASSWORD = "demo1234"
DEMO_USERS = [
    {"email": "danagul@ahtama.demo", "name": "Danagul", "role": "owner"},
    {"email": "aisha@ahtama.demo", "name": "Aisha", "role": "member"},
    {"email": "fatima@ahtama.demo", "name": "Fatima", "role": "caregiver"},
]


def seed():
    db = SessionLocal()
    try:
        if db.query(User).first():
            return
        users = []
        for u in DEMO_USERS:
            user = User(email=u["email"], name=u["name"], password_hash=hash_password(DEMO_PASSWORD))
            db.add(user)
            users.append((user, u["role"]))
        db.flush()
        circle = CareCircle(recipient_name="Ahmed Al-Karim", recipient_dob="1947-03-02",
                            recipient_notes="MRN SAMPLE-2048-DOH · Al Waab, Doha",
                            owner_user_id=users[0][0].id, consent_recorded_at=now(),
                            invite_code="AHMED123")
        db.add(circle)
        db.flush()
        for user, role in users:
            db.add(Membership(user_id=user.id, circle_id=circle.id, role=role))
        db.add(Task(circle_id=circle.id, title="Upload the latest discharge letter", source="manual"))
        db.commit()
        print("Seeded demo data: circle for Ahmed Al-Karim, users danagul/aisha/fatima "
              f"@ahtama.demo (password: {DEMO_PASSWORD})")
    finally:
        db.close()
