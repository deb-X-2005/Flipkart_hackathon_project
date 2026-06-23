"""CatBoost forecaster for requires_road_closure."""
from pathlib import Path
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool

NUM_COLS = ["latitude", "longitude", "hour", "dow", "month", "is_weekend"]
CAT_COLS = ["event_type", "event_cause", "priority", "zone", "corridor", "junction", "police_station"]
TARGET = "requires_road_closure"


def prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    keep = [c for c in NUM_COLS + CAT_COLS if c in df.columns]
    X = df[keep].copy()
    for c in CAT_COLS:
        if c in X.columns:
            X[c] = X[c].astype("string").fillna("__missing__")
    for c in NUM_COLS:
        if c in X.columns:
            X[c] = pd.to_numeric(X[c], errors="coerce")
    y = df[TARGET].astype(int)
    return X, y


def train(X_train, y_train, cat_features, class_weights=None, iterations=400) -> CatBoostClassifier:
    model = CatBoostClassifier(
        iterations=iterations,
        depth=6,
        learning_rate=0.05,
        loss_function="Logloss",
        eval_metric="F1",
        class_weights=class_weights,
        random_seed=42,
        verbose=False,
    )
    model.fit(Pool(X_train, y_train, cat_features=cat_features))
    return model


def save(model: CatBoostClassifier, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(path))


def load(path: Path) -> CatBoostClassifier:
    m = CatBoostClassifier()
    m.load_model(str(path))
    return m
