import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

def content_based_recommendation(courses_df, course_title, top_n=5):

    courses_df = courses_df.fillna("")

    courses_df["content"] = (
        courses_df["title"] + " " +
        courses_df["organization"] + " " +
        courses_df["level"]
    )

    tfidf = TfidfVectorizer(stop_words="english")

    tfidf_matrix = tfidf.fit_transform(courses_df["content"])

    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

    indices = pd.Series(courses_df.index, index=courses_df["title"]).drop_duplicates()

    if course_title not in indices:
        return courses_df.head(top_n)

    idx = indices[course_title]

    sim_scores = list(enumerate(cosine_sim[idx]))

    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    sim_scores = sim_scores[1:top_n+1]

    course_indices = [i[0] for i in sim_scores]

    return courses_df.iloc[course_indices]

def collaborative_filtering(ratings_df, courses_df, user_id, top_n=5):

    if ratings_df.empty:
        return courses_df.sample(top_n)

    user_item_matrix = ratings_df.pivot_table(
        index="user_id",
        columns="course_id",
        values="rating",
        aggfunc="mean"
    ).fillna(0)

    user_similarity = cosine_similarity(user_item_matrix)

    user_similarity_df = pd.DataFrame(
        user_similarity,
        index=user_item_matrix.index,
        columns=user_item_matrix.index
    )

    if user_id not in user_similarity_df.index:
        return courses_df.sample(top_n)

    similar_users = user_similarity_df[user_id].sort_values(ascending=False)[1:6]

    similar_user_ids = similar_users.index

    recommended_courses = ratings_df[
        ratings_df["user_id"].isin(similar_user_ids)
    ]["course_id"].value_counts().head(top_n)

    return courses_df[courses_df["id"].isin(recommended_courses.index)]

def matrix_factorization(ratings_df, courses_df, user_id, top_n=5):

    if ratings_df.empty:
        return courses_df.sample(top_n)

    user_item_matrix = ratings_df.pivot_table(
        index="user_id",
        columns="course_id",
        values="rating",
        aggfunc="mean"
    ).fillna(0)

    svd = TruncatedSVD(n_components=10)

    matrix = svd.fit_transform(user_item_matrix)

    reconstructed_matrix = np.dot(matrix, svd.components_)

    reconstructed_df = pd.DataFrame(
        reconstructed_matrix,
        index=user_item_matrix.index,
        columns=user_item_matrix.columns
    )

    if user_id not in reconstructed_df.index:
        return courses_df.sample(top_n)

    user_predictions = reconstructed_df.loc[user_id]

    top_courses = user_predictions.sort_values(ascending=False).head(top_n)

    return courses_df[courses_df["id"].isin(top_courses.index)]

def hybrid_recommendation(courses_df, ratings_df, user_id, top_n=5):

    try:

        collab = collaborative_filtering(ratings_df, courses_df, user_id, top_n)

        matrix = matrix_factorization(ratings_df, courses_df, user_id, top_n)

        combined = pd.concat([collab, matrix])

        combined = combined.drop_duplicates(subset="id")

        return combined.head(top_n)

    except:

        return courses_df.sample(top_n)