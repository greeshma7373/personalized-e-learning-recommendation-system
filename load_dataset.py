import pandas as pd
from sqlalchemy import create_engine
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

dataset_path = os.path.join(BASE_DIR, "dataset", "coursea_data.csv")

df = pd.read_csv(dataset_path)

engine = create_engine("postgresql://postgres:post9849@localhost/elearning_db")

df = df.rename(columns={
    "course_title": "title",
    "course_organization": "organization",
    "course_Certificate_type": "certificate_type",
    "course_rating": "rating",
    "course_level": "level",
    "course_students_enrolled": "students_enrolled"
})

df[['title','organization','certificate_type','rating','level','students_enrolled']].to_sql(
    "courses",
    engine,
    if_exists="append",
    index=False
)

print("Dataset inserted successfully")