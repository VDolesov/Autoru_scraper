import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from joblib import dump

DATA_FILE = Path("search_results_after_improvements.csv")
VECTORIZER_PATH = Path("tfidf_vectorizer.pkl")
RF_MODEL_PATH = Path("random_forest_model.pkl")
LR_MODEL_PATH = Path("logistic_regression_model.pkl")


def load_data():
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    y = df["Релевантность"].astype(int)
    text = (
        df["Запрос"].astype(str)
        + " "
        + df["Заголовок"].astype(str)
        + " "
        + df["Текст"].astype(str)
        + " "
        + df["Категория"].astype(str)
    )
    return text, y


def main():
    X_text, y = load_data()

    X_train_text, X_test_text, y_train, y_test = train_test_split(
        X_text,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.9
    )

    X_train = vectorizer.fit_transform(X_train_text)
    X_test = vectorizer.transform(X_test_text)

    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        n_jobs=-1,
        random_state=42
    )

    lr = LogisticRegression(
        max_iter=1000,
        n_jobs=-1
    )

    rf.fit(X_train, y_train)
    lr.fit(X_train, y_train)

    y_pred_rf = rf.predict(X_test)
    y_pred_lr = lr.predict(X_test)

    print("=== RandomForest ===")
    print("Accuracy:", accuracy_score(y_test, y_pred_rf))
    print(classification_report(y_test, y_pred_rf, digits=3))

    print("\n=== LogisticRegression ===")
    print("Accuracy:", accuracy_score(y_test, y_pred_lr))
    print(classification_report(y_test, y_pred_lr, digits=3))

    X_full = vectorizer.fit_transform(X_text)
    rf_full = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        n_jobs=-1,
        random_state=42
    )
    lr_full = LogisticRegression(
        max_iter=1000,
        n_jobs=-1
    )
    rf_full.fit(X_full, y)
    lr_full.fit(X_full, y)

    dump(vectorizer, VECTORIZER_PATH)
    dump(rf_full, RF_MODEL_PATH)
    dump(lr_full, LR_MODEL_PATH)

    print("\nМодели и векторизатор сохранены:")
    print(" ", VECTORIZER_PATH)
    print(" ", RF_MODEL_PATH)
    print(" ", LR_MODEL_PATH)


if __name__ == "__main__":
    main()
