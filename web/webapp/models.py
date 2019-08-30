"""Database Models using Flask SQLAlchemy as ORM"""
import os

from .app import db

class Inquiry(db.Model):
    """Questions, Answers, and the amount of times it has been asked."""
    __tablename__ = "inquiries"

    _id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text)
    times_asked = db.Column(db.Integer)

    def __init__(self, question, answer):
        if not db.session.query(db.exists().where(Inquiry.question == question)).scalar():
            self.question = question.lower()
            self.answer = answer.lower()
            self.times_asked = 0
        else:
            raise ValueError('This question already exists.')
