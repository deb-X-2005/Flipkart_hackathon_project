"""Stage 4: train CatBoost on requires_road_closure.
Compare: (a) class_weights only, (b) SMOTE-NC synthetic minority oversampling.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
from imblearn.over_sampling import SMOTENC

from src.config import DATA_PROCESSED, ROOT
from src.models.forecast import prepare, train, save, CAT_COLS


def evaluate(name, model, X_te, y_te):
    p = model.predict_proba(X_te)[:, 1]
    yhat = (p >= 0.5).astype(int)
    print(f"\n--- {name} ---")
    print(classification_report(y_te, yhat, digits=3, zero_division=0))
    print(f"ROC-AUC: {roc_auc_score(y_te, p):.3f}")
    print(f"confusion (rows=actual, cols=pred):\n{confusion_matrix(y_te, yhat)}")
    return p, yhat


def main() -> None:
    df = pd.read_csv(DATA_PROCESSED / "events.csv")
    df = df.dropna(subset=["requires_road_closure"])
    X, y = prepare(df)
    cat_features = [c for c in CAT_COLS if c in X.columns]

    print(f"rows: {len(X):,}  features: {X.shape[1]}  positives: {y.sum()} ({y.mean()*100:.1f}%)")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    # (a) class weights only
    neg, pos = (y_tr == 0).sum(), (y_tr == 1).sum()
    class_weights = [1.0, neg / max(pos, 1)]
    m_a = train(X_tr, y_tr, cat_features, class_weights=class_weights)
    evaluate("CatBoost + class_weights", m_a, X_te, y_te)

    # (b) SMOTE-NC synthetic oversampling
    # SMOTE-NC needs numeric cats -> use codes; reverse mapping after
    X_tr_enc = X_tr.copy()
    cat_idx = [X_tr_enc.columns.get_loc(c) for c in cat_features]
    cat_maps = {}
    for c in cat_features:
        cats = X_tr_enc[c].astype("category")
        cat_maps[c] = list(cats.cat.categories)
        X_tr_enc[c] = cats.cat.codes  # int codes
    for c in [col for col in X_tr_enc.columns if col not in cat_features]:
        X_tr_enc[c] = X_tr_enc[c].fillna(X_tr_enc[c].median())

    sm = SMOTENC(categorical_features=cat_idx, random_state=42, k_neighbors=5)
    X_res, y_res = sm.fit_resample(X_tr_enc, y_tr)
    # decode back to strings for CatBoost
    for c, cats in cat_maps.items():
        codes = X_res[c].astype(int).clip(0, len(cats) - 1)
        X_res[c] = [cats[i] for i in codes]
    print(f"\nSMOTE-NC: {len(X_tr):,} -> {len(X_res):,} rows  (positives: {y_res.sum()})")
    m_b = train(X_res, y_res, cat_features, class_weights=None)
    evaluate("CatBoost + SMOTE-NC", m_b, X_te, y_te)

    # save the better one by AUC
    auc_a = roc_auc_score(y_te, m_a.predict_proba(X_te)[:, 1])
    auc_b = roc_auc_score(y_te, m_b.predict_proba(X_te)[:, 1])
    winner, m_best = ("class_weights", m_a) if auc_a >= auc_b else ("smote", m_b)
    out = ROOT / "models" / "closure_clf.cbm"
    save(m_best, out)
    print(f"\nwinner: {winner}  (auc_a={auc_a:.3f}, auc_b={auc_b:.3f}) -> {out}")

    print("\nfeature importance (top 10):")
    fi = pd.Series(m_best.get_feature_importance(), index=X.columns).sort_values(ascending=False).head(10)
    print(fi.round(2))


if __name__ == "__main__":
    main()
