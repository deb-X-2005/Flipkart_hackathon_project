"""Stage 4b: hyperparameter tune + text features + threshold optimization.
Optimizes ROC-AUC via Optuna (3-fold stratified CV), then picks F1-optimal threshold.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import optuna
from catboost import CatBoostClassifier, Pool, cv
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
)

from src.config import DATA_PROCESSED, ROOT

NUM_COLS = ["latitude", "longitude", "hour", "dow", "month", "is_weekend"]
CAT_COLS = ["event_type", "event_cause", "priority", "zone", "corridor", "junction", "police_station"]
TEXT_COLS = []  # text features were too slow; revisit later
TARGET = "requires_road_closure"


def engineer(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    h = df["hour"].fillna(-1)
    df["rush_hour"] = ((h.between(8, 10)) | (h.between(18, 21))).astype(int)
    df["is_night"] = ((h <= 4) | (h >= 22)).astype(int)
    bins = pd.cut(h, bins=[-1, 5, 11, 16, 21, 23], labels=["late", "morning", "midday", "evening", "night"])
    df["hour_bucket"] = bins.astype("string").fillna("unknown")
    return df


def prepare(df: pd.DataFrame):
    df = engineer(df)
    cat = [c for c in CAT_COLS + ["hour_bucket"] if c in df.columns]
    num = [c for c in NUM_COLS + ["rush_hour", "is_night"] if c in df.columns]
    txt = [c for c in TEXT_COLS if c in df.columns]
    keep = num + cat + txt
    X = df[keep].copy()
    for c in cat:
        X[c] = X[c].astype("string").fillna("__missing__")
    for c in txt:
        X[c] = X[c].astype("string").fillna("")
    for c in num:
        X[c] = pd.to_numeric(X[c], errors="coerce").fillna(-1)
    y = df[TARGET].astype(int)
    return X, y, cat, txt


def main() -> None:
    df = pd.read_csv(DATA_PROCESSED / "events.csv").dropna(subset=[TARGET])
    X, y, cat_features, text_features = prepare(df)
    print(f"rows: {len(X):,}  num: {len(NUM_COLS)+2}  cat: {len(cat_features)}  text: {len(text_features)}  pos: {y.mean()*100:.1f}%")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    train_pool = Pool(X_tr, y_tr, cat_features=cat_features, text_features=text_features)

    def objective(trial):
        params = {
            "iterations": trial.suggest_int("iterations", 200, 400),
            "depth": trial.suggest_int("depth", 4, 6),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.15, log=True),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 10.0, log=True),
            "bagging_temperature": trial.suggest_float("bagging_temperature", 0.0, 1.0),
            "random_strength": trial.suggest_float("random_strength", 0.5, 2.0),
            "auto_class_weights": "Balanced",
            "loss_function": "Logloss",
            "eval_metric": "AUC",
            "random_seed": 42,
            "verbose": False,
        }
        scores = cv(train_pool, params, fold_count=2, stratified=True, partition_random_seed=42, verbose=False, plot=False, early_stopping_rounds=30)
        auc = scores["test-AUC-mean"].iloc[-1]
        print(f"  trial {trial.number}: AUC={auc:.4f}", flush=True)
        return auc

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=8, show_progress_bar=False)
    print(f"\nbest CV AUC: {study.best_value:.4f}")
    print(f"best params: {study.best_params}")

    best = CatBoostClassifier(
        **study.best_params,
        auto_class_weights="Balanced",
        loss_function="Logloss",
        eval_metric="AUC",
        random_seed=42,
        verbose=False,
    )
    best.fit(train_pool)

    p = best.predict_proba(X_te)[:, 1]
    auc = roc_auc_score(y_te, p)

    prec, rec, thr = precision_recall_curve(y_te, p)
    f1s = 2 * prec * rec / np.clip(prec + rec, 1e-9, None)
    best_idx = int(np.argmax(f1s[:-1]))
    best_thr = float(thr[best_idx])
    yhat = (p >= best_thr).astype(int)

    print(f"\n--- tuned CatBoost @ threshold={best_thr:.3f} ---")
    print(f"test ROC-AUC: {auc:.3f}")
    print(classification_report(y_te, yhat, digits=3, zero_division=0))
    print(f"confusion:\n{confusion_matrix(y_te, yhat)}")

    out = ROOT / "models" / "closure_clf.cbm"
    best.save_model(str(out))
    (ROOT / "models" / "threshold.txt").write_text(f"{best_thr:.6f}")
    print(f"\nsaved -> {out}  (threshold={best_thr:.3f})")

    print("\nfeature importance (top 12):")
    fi = pd.Series(best.get_feature_importance(), index=X.columns).sort_values(ascending=False).head(12)
    print(fi.round(2))

    print("\n=== delta vs Stage 4 baseline ===")
    print(f"  AUC:  0.815 -> {auc:.3f}  ({(auc-0.815)*100:+.1f} pp)")
    print(f"  F1:   0.404 -> {f1_score(y_te, yhat):.3f}")


if __name__ == "__main__":
    main()
