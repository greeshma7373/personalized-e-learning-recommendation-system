import pandas as pd
import matplotlib.pyplot as plt
def course_rating_chart(courses):
    df = pd.DataFrame(courses)
    plt.hist(df["rating"])
    plt.title("Course Ratings Distribution")
    plt.xlabel("Rating")
    plt.ylabel("Count")
    plt.show()