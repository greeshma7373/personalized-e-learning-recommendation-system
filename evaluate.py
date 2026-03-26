import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import mean_squared_error
from math import sqrt
engine = create_engine("postgresql://postgres:post9849@localhost/elearning_db")

def load_data():
    ratings_df = pd.read_sql("SELECT user_id, course_id, rating FROM ratings", engine)
    return ratings_df

def matrix_factorization(ratings_df):

    pivot = ratings_df.pivot_table(
        index='user_id',
        columns='course_id',
        values='rating'
    )

    pivot_filled = pivot.fillna(0)

    global_mean = ratings_df['rating'].mean()

    user_bias = pivot.mean(axis=1) - global_mean
    item_bias = pivot.mean(axis=0) - global_mean

    user_bias = user_bias.fillna(0)
    item_bias = item_bias.fillna(0)

    # Normalize
    pivot_centered = pivot.copy()

    for user in pivot.index:
        pivot_centered.loc[user] = pivot.loc[user] - (global_mean + user_bias[user])

    pivot_centered = pivot_centered.fillna(0)

    # SVD
    svd = TruncatedSVD(n_components=15, random_state=42)
    latent = svd.fit_transform(pivot_centered)
    reconstructed = np.dot(latent, svd.components_)

    predicted = reconstructed.copy()

    for i, user in enumerate(pivot.index):
        for j, item in enumerate(pivot.columns):
            predicted[i][j] = (
                global_mean
                + 0.5 * user_bias[user]
                + 0.5 * item_bias[item]
                + reconstructed[i][j]
            )

    # Clip ratings
    predicted = np.clip(predicted, 1, 5)

    predicted_df = pd.DataFrame(
        predicted,
        index=pivot.index,
        columns=pivot.columns
    )

    return predicted_df

def compute_rmse(ratings_df, predicted_df):

    actual = []
    predicted = []

    for _, row in ratings_df.iterrows():
        user = row['user_id']
        course = row['course_id']

        if user in predicted_df.index and course in predicted_df.columns:
            actual.append(row['rating'])
            predicted.append(predicted_df.loc[user, course])

    return sqrt(mean_squared_error(actual, predicted))



def compute_metrics(ratings_df, predicted_df, k=10, threshold=3.5):

    precision_list = []
    recall_list = []

    course_popularity = ratings_df.groupby('course_id')['rating'].count()
    course_popularity = course_popularity / course_popularity.max()

    for user in predicted_df.index:

        if user not in ratings_df['user_id'].values:
            continue

        user_actual = ratings_df[ratings_df['user_id'] == user]

        relevant_items = user_actual[user_actual['rating'] >= threshold]['course_id'].tolist()

        if len(relevant_items) == 0:
            continue

        scores = predicted_df.loc[user]

        # Add popularity boost
        final_scores = scores.copy()

        for course in final_scores.index:
            if course in course_popularity:
                final_scores[course] += 0.3 * course_popularity[course]

        # Top-K
        top_k = final_scores.sort_values(ascending=False).head(k).index.tolist()

        # Compute metrics
        relevant_set = set(relevant_items)
        recommended_set = set(top_k)

        true_positive = len(relevant_set & recommended_set)

        precision = true_positive / k
        recall = true_positive / len(relevant_set)

        precision_list.append(precision)
        recall_list.append(recall)

    avg_precision = np.mean(precision_list) if precision_list else 0
    avg_recall = np.mean(recall_list) if recall_list else 0

    if avg_precision + avg_recall == 0:
        f1 = 0
    else:
        f1 = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall)

    return avg_precision, avg_recall, f1


def evaluate_model(k=10):

    print("\n MODEL EVALUATION RESULTS\n")

    ratings_df = load_data()

    predicted_df = matrix_factorization(ratings_df)

    rmse = compute_rmse(ratings_df, predicted_df)

    precision, recall, f1 = compute_metrics(ratings_df, predicted_df, k=k)

    print(f"RMSE Score        : {rmse:.4f}")
    print(f"Precision@{k}     : {precision:.4f}")
    print(f"Recall@{k}        : {recall:.4f}")
    print(f"F1 Score@{k}      : {f1:.4f}")

    print("\n Evaluation Completed")

if __name__ == "__main__":
    evaluate_model(k=10)