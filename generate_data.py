import random
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("postgresql://postgres:post9849@localhost/elearning_db")
-
courses_df = pd.read_sql("SELECT * FROM courses", engine)

users = []
for i in range(1, 51):
    users.append({
        "name": f"User{i}",
        "email": f"user{i}@gmail.com",
        "password": "123"
    })

users_df = pd.DataFrame(users)

# Insert users
users_df.to_sql("users", engine, if_exists="replace", index=False)

print(" Users inserted")

# GET USER IDs
users_db = pd.read_sql("SELECT id FROM users", engine)

user_ids = users_db["id"].tolist()
course_ids = courses_df["id"].tolist()

# GENERATE RATINGS (REALISTIC)
# GENERATE STRONG REALISTIC RATINGS


ratings = []

course_categories = {}

for cid in course_ids:
    course_categories[cid] = random.choice(["Python", "ML", "Web", "Data"])

for user in user_ids:
    user_pref = random.choice(["Python", "ML", "Web", "Data"])

    rated_courses = random.sample(course_ids, k=random.randint(15, 40))

    for course in rated_courses:

        course_cat = course_categories[course]
        if course_cat == user_pref:
            rating = random.choice([4, 5])   
        else:
            rating = random.choice([1, 2, 3]) 

        ratings.append({
            "user_id": int(user),
            "course_id": int(course),
            "rating": int(rating)
        })

ratings_df = pd.DataFrame(ratings)

ratings_df.to_sql("ratings", engine, if_exists="replace", index=False)

print(f" {len(ratings_df)} STRONG ratings inserted")