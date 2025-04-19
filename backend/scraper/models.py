from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    logo_link = db.Column(db.String(255))
    company = db.Column(db.String(255))
    description = db.Column(db.Text)
    responsibilities = db.Column(db.Text)
    requirements = db.Column(db.Text)
    location = db.Column(db.String(255))
    experience_level = db.Column(db.String(255))
    salary = db.Column(db.Text)
    other = db.Column(db.Text)
    posted_date = db.Column(db.DateTime)
    embedding = db.Column(db.Text)
    quick_apply_url = db.Column(db.String(255))
    job_url = db.Column(db.String(255))
