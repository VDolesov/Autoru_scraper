#ручное предсказание
from pathlib import Path
from joblib import load

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

VECTORIZER_PATH = Path("tfidf_vectorizer.pkl")
RF_MODEL_PATH = Path("random_forest_model.pkl")
LR_MODEL_PATH = Path("logistic_regression_model.pkl")


def load_models():
    vectorizer: TfidfVectorizer = load(VECTORIZER_PATH)
    rf: RandomForestClassifier = load(RF_MODEL_PATH)
    lr: LogisticRegression = load(LR_MODEL_PATH)
    return vectorizer, rf, lr


def build_text(query: str, title: str, text: str, category: str) -> str:
    return " ".join([query.strip(), title.strip(), text.strip(), category.strip()])


def main():
    if not VECTORIZER_PATH.exists() or not RF_MODEL_PATH.exists() or not LR_MODEL_PATH.exists():
        print("Сначала запусти train_models.py, чтобы обучить и сохранить модели.")
        return

    vectorizer, rf, lr = load_models()

    print("=== ML-предсказание релевантности (Auto.ru) ===")

    while True:
        query = input("\nЗапрос (пусто = выход): ").strip()
        if not query:
            break
        title = input("Заголовок статьи: ").strip()
        text = input("Текст статьи (можно укороченный): ").strip()
        category = input("Категория: ").strip()

        full_text = build_text(query, title, text, category)
        X = vectorizer.transform([full_text])

        proba_rf = rf.predict_proba(X)[0, 1]
        proba_lr = lr.predict_proba(X)[0, 1]

        print(f"\nВероятность релевантности:")
        print(f"  RandomForest:       {proba_rf:.3f}")
        print(f"  LogisticRegression: {proba_lr:.3f}")


if __name__ == "__main__":
    main()
