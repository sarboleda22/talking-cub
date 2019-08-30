"""Script to be run on boot/startup"""
import time
from webapp.app import app, db
from webapp.models import Inquiry
from webapp.config import MAX_INQUIRIES

def wait_for_postgres():
    try:
        db.engine.execute("SELECT 1")
        print("connected to db")
        return None
    except Exception as e:
        print("Error while trying to connect to the DB: {}".format(e))
        time.sleep(2)
        wait_for_postgres()


def create_items():
    """Create all inquiries in the DB if non-existent."""
    if not any(Inquiry.query.all()):
        print("Creating Initial Sample Questions...")
        sample_q = "Sample Question?"
        sample_ans = "Sample Answer."
        for _ in range(MAX_INQUIRIES):
            new_inquiry = Inquiry(
                sample_q,
                sample_ans
            )
            db.session.add(new_inquiry)
    db.session.commit()

wait_for_postgres()
db.create_all()
create_items()

if __name__ == '__main__':
    app.run()
