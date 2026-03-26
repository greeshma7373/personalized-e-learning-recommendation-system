from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100))

    email = db.Column(db.String(120), unique=True)

    password = db.Column(db.String(200))

class Course(db.Model):

    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.Text)

    organization = db.Column(db.Text)

    certificate_type = db.Column(db.Text)

    rating = db.Column(db.Float)

    level = db.Column(db.Text)

    students_enrolled = db.Column(db.Text)


class Rating(db.Model):

    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer)

    course_id = db.Column(db.Integer)

    rating = db.Column(db.Float)


class Progress(db.Model):

    __tablename__ = "progress"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer)

    course_id = db.Column(db.Integer)

    progress = db.Column(db.Integer)