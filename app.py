from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import create_engine
from models import db, User, Course, Rating, Progress
from recommendation import hybrid_recommendation
import numpy as np
app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)
app.secret_key = "secret123"
engine = create_engine("postgresql://postgres:post9849@localhost:5432/elearning_db")
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:post9849@localhost/elearning_db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
def semantic_search(courses_df, query):
    tfidf = TfidfVectorizer(stop_words="english")
    text_data = courses_df["title"] + " " + courses_df["organization"]
    tfidf_matrix = tfidf.fit_transform(text_data)
    query_vec = tfidf.transform([query])
    similarity = cosine_similarity(query_vec, tfidf_matrix)
    scores = similarity.flatten()
    courses_df["score"] = scores
    results = courses_df.sort_values(by="score", ascending=False)
    return results.head(10)
def generate_reason(user_id, course_title, ratings_df, courses_df):
    user_data = ratings_df[(ratings_df['user_id'] == user_id) & (ratings_df['rating'] >= 4)]
    if user_data.empty:
        return "Popular among learners"
    liked_courses = user_data.merge(courses_df, left_on='course_id', right_on='id')
    liked_titles = liked_courses['title'].tolist()
    keywords = []
    for title in liked_titles:
        words = title.lower().split()
        keywords.extend(words)

    # Count frequent words
    from collections import Counter
    common_words = [word for word, _ in Counter(keywords).most_common(3)]

    if common_words:
        return f"Recommended because you liked {' & '.join(common_words)} courses"

    return "Recommended for you"


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("login.html")


# ---------------- REGISTER ----------------

from sqlalchemy import text

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        with engine.begin() as conn:

            existing = conn.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email}
            ).fetchone()

            if existing:
                return redirect(url_for('login', message="already_exists"))
                message = request.args.get('message')
                return render_template('register.html',message=message)

            result = conn.execute(text("""
                INSERT INTO users (name, email, password)
                VALUES (:name, :email, :password)
                RETURNING id
            """), {
                "name": name,
                "email": email,
                "password": password
            })

            user_id = result.fetchone()[0]
        session.clear()
        session['user_id'] = int(user_id)

        return redirect('/courses')

    return render_template('register.html')

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email, password=password).first()

        if user:
            session["user_id"] = user.id
            return redirect("/courses")
        else:
            return "Invalid credentials"

    return render_template("login.html")

# ---------------- COURSES PAGE ----------------

@app.route('/courses')
def courses():

    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    search_query = request.args.get('search', '').strip().lower()
    levels = request.args.getlist('level')
    sort_option = request.args.get('sort')

    # ---------------- LOAD DATA ----------------
    courses_df = pd.read_sql("SELECT * FROM courses", engine)
    ratings_df = pd.read_sql("SELECT * FROM ratings", engine)

    # Clean level column
    courses_df['level'] = courses_df['level'].fillna('').str.strip()

    # Remove low-quality courses
    courses_df = courses_df[courses_df['rating'] >= 3]

    # ---------------- AVG RATINGS ----------------
    avg_ratings = ratings_df.groupby('course_id')['rating'].mean().reset_index()
    avg_dict = dict(zip(avg_ratings['course_id'], avg_ratings['rating']))

    # ---------------- FILTERED COURSES (ALL COURSES SECTION) ----------------
    filtered_courses = courses_df.copy()

    if search_query:
        filtered_courses = filtered_courses[
            filtered_courses['title'].str.lower().str.contains(search_query, na=False)
        ]

    if levels:
        filtered_courses = filtered_courses[
            filtered_courses['level'].str.lower().isin([lvl.lower() for lvl in levels])
        ]

    # ---------------- HYBRID RECOMMENDATION ----------------
    course_popularity = ratings_df.groupby('course_id')['rating'].mean().to_dict()
    user_ratings = ratings_df[ratings_df['user_id'] == user_id]

    recommendation_scores = []

    for _, row in courses_df.iterrows():

        course_id = row['id']

        # Popularity score
        pop_score = course_popularity.get(course_id, 0)

        # User preference score
        user_score = 0
        if not user_ratings.empty:
            if course_id in user_ratings['course_id'].values:
                user_score = user_ratings[
                    user_ratings['course_id'] == course_id
                ]['rating'].values[0]

        # Hybrid score
        final_score = (0.7 * pop_score) + (0.3 * user_score)
        final_score = np.clip(final_score, 0, 5)

        recommendation_scores.append((course_id, final_score))

    # Sort recommendations
    recommendation_scores = sorted(
        recommendation_scores,
        key=lambda x: x[1],
        reverse=True
    )

    # Top IDs
    top_ids = [cid for cid, _ in recommendation_scores[:10]]

    recs = courses_df[courses_df['id'].isin(top_ids)]

    # ---------------- APPLY FILTERS TO RECOMMENDATIONS ----------------
    if search_query:
        recs = recs[recs['title'].str.lower().str.contains(search_query, na=False)]

    if levels:
        recs = recs[
            recs['level'].str.lower().isin([lvl.lower() for lvl in levels])
        ]

    # ---------------- BOOST SIMILAR COURSES ----------------
    if not user_ratings.empty:
        liked_titles = courses_df[
            courses_df['id'].isin(user_ratings['course_id'])
        ]['title'].tolist()

        if liked_titles:
            pattern = '|'.join(liked_titles[:3])
            similar = courses_df[
                courses_df['title'].str.contains(pattern, case=False, na=False)
            ]

            recs = pd.concat([similar, recs]).drop_duplicates().head(10)

    # ---------------- BUILD RECOMMENDATIONS ----------------
    top_recommendations = []

    for _, row in recs.iterrows():

        avg_rating = round(avg_dict.get(row['id'], 0), 1)

        #  Reason logic
        if not user_ratings.empty and row['id'] in user_ratings['course_id'].values:
            reason = "Because you rated similar courses"
        elif avg_rating >= 4:
            reason = "Highly rated by learners"
        else:
            reason = "Trending course"

        top_recommendations.append({
            "id": int(row['id']),
            "title": row['title'],
            "avg_rating": float(avg_rating),
            "reason": reason
        })

    # ---------------- REMOVE DUPLICATES FROM ALL COURSES ----------------
    filtered_courses = filtered_courses[
        ~filtered_courses['id'].isin([r["id"] for r in top_recommendations])
    ]

    # ---------------- BUILD ALL COURSES ----------------
    all_courses = []

    for _, row in filtered_courses.iterrows():

        avg_rating = round(avg_dict.get(row['id'], 0), 1)

        all_courses.append({
            "id": int(row['id']),
            "title": row['title'],
            "avg_rating": float(avg_rating),
            "level": row['level']
        })

    # ---------------- SORTING ----------------
    if sort_option == "rating_high":
        all_courses = sorted(
            all_courses,
            key=lambda x: (x['avg_rating'] == 0, -x['avg_rating'])
        )

    elif sort_option == "rating_low":
        all_courses = sorted(
            all_courses,
            key=lambda x: (x['avg_rating'] == 0, x['avg_rating'])
        )

    # ---------------- FINAL RENDER ----------------
    return render_template(
        'courses.html',
        top_recommendations=top_recommendations,
        all_courses=all_courses
    )
    
# ---------------- RATE COURSE ----------------

@app.route("/rate", methods=["POST"])
def rate():

    user_id = session["user_id"]
    course_id = request.form["course_id"]
    rating = request.form["rating"]

    new_rating = Rating(
        user_id=user_id,
        course_id=course_id,
        rating=rating
    )

    db.session.add(new_rating)
    db.session.commit()

    return redirect("/courses")

#-------------------rate course-----------------
from sqlalchemy import text


@app.route('/rate_course', methods=['POST'])
def rate_course():

    user_id = session.get('user_id')
    course_id = request.form.get('course_id')
    rating = request.form.get('rating')

    if not user_id:
        return redirect('/login')

    existing = pd.read_sql(
        text("SELECT * FROM ratings WHERE user_id=:u AND course_id=:c"),
        engine,
        params={"u": user_id, "c": course_id}
    )

    with engine.connect() as conn:

        if not existing.empty:
            conn.execute(
                text("""
                    UPDATE ratings 
                    SET rating = :rating
                    WHERE user_id = :user_id AND course_id = :course_id
                """),
                {"rating": rating, "user_id": user_id, "course_id": course_id}
            )
        else:
            conn.execute(
                text("""
                    INSERT INTO ratings (user_id, course_id, rating)
                    VALUES (:user_id, :course_id, :rating)
                """),
                {"user_id": user_id, "course_id": course_id, "rating": rating}
            )

        conn.commit()

    return redirect('/courses')

# ---------------- COURSE PROGRESS ----------------

@app.route("/progress/<int:course_id>")
def progress(course_id):

    user_id = session["user_id"]

    record = Progress.query.filter_by(
        user_id=user_id,
        course_id=course_id
    ).first()

    if record:
        record.progress += 20
        if record.progress > 100:
            record.progress = 100
    else:
        record = Progress(
            user_id=user_id,
            course_id=course_id,
            progress=20
        )
        db.session.add(record)

    db.session.commit()

    return redirect("/dashboard")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    user_id = session["user_id"]

    progress = Progress.query.filter_by(user_id=user_id).all()

    courses = Course.query.all()

    course_dict = {c.id: c.title for c in courses}
    
    rated_courses = pd.read_sql(text("""
        SELECT c.title, r.rating
        FROM ratings r
        JOIN courses c ON r.course_id = c.id
        WHERE r.user_id = :user_id
        """), engine, params={"user_id": user_id})
    rated_list = rated_courses.to_dict(orient='records')

    return render_template(
        "dashboard.html",
        progress=progress,
        course_dict=course_dict,
        rated_courses=rated_list
    )

# ---------------- ANALYTICS ----------------

@app.route("/analytics")
def analytics():

    courses = pd.read_sql("SELECT * FROM courses", db.engine)
    ratings = pd.read_sql("SELECT * FROM ratings", db.engine)

    rating_counts = ratings.groupby("rating").size().to_dict()

    level_counts = courses.groupby("level").size().to_dict()

    return render_template(
        "analytics.html",
        rating_counts=rating_counts,
        level_counts=level_counts
    )


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ---------------- RUN APP ----------------

if __name__ == "__main__":

    app.run(debug=True)

