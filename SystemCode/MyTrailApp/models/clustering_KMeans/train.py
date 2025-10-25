# -*- coding: utf-8 -*-
"""
用法：
  python train_routes.py --data /mnt/data/synthetic_data.jsonl --outdir ./out \
    --auto-k 2 10
或手动指定 k：
  python train_routes.py --k 5
"""
import json
import re
import argparse
from pathlib import Path
from typing import Any, Dict, List
from collections import Counter, defaultdict
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import MiniBatchKMeans, KMeans
from sklearn.metrics import silhouette_score
import joblib
from route_feature import RouteFeatureExtractor, parse_duration_seconds, safe_get, viewport_area, duration_per_km



# ---------- 主题命名 ----------
def distance_bucket(distance_m: float) -> str:
    if np.isnan(distance_m): return "Unknown"
    km = distance_m / 1000.0
    if km < 5: return "Short"
    elif km < 10: return "Medium"
    else: return "Long"
    
def infer_theme_name(routes_in_cluster: List[Dict[str, Any]]) -> str:
    cat_counter = Counter()
    distances, ratings = [], []
    for r in routes_in_cluster:
        distances.append(r.get("distance", np.nan))
        for w in r.get("waypoints", []) or []:
            for key in ("category", "search_category"):
                c = (w.get(key) or "").strip().title()
                if c:
                    cat_counter[c] += 1
        rv = [w.get("rating") for w in r.get("waypoints", []) or [] if w.get("rating") is not None]
        ratings.extend(rv)

    top = cat_counter.most_common(2)
    if top and (len(top) == 1 or (len(top) == 2 and top[0][1] >= top[1][1] * 1.2)):
        theme = top[0][0]
        if theme.lower() in {"park", "nature", "scenic"} and len(top) >= 2:
            return f"{top[0][0]} & {top[1][0]}"
        return theme

    dist_med = np.nanmedian(distances) if distances else np.nan
    bucket = distance_bucket(dist_med if pd.notna(dist_med) else np.nan)
    if ratings:
        m = float(np.mean(ratings))
        suffix = "Scenic" if m >= 4.5 else ("Popular" if m >= 4.2 else "Urban Mix")
    else:
        suffix = "Mixed"
    return f"{bucket} • {suffix}"


# ---------- 读取你上传的文件 ----------
def load_routes_tolerant(path: Path) -> List[Dict[str, Any]]:
    txt = path.read_text(encoding="utf-8")
    # 尝试当成“一个 JSON 数组的内容”来包裹
    wrapped = "[" + txt + "]"
    wrapped = re.sub(r",\s*\]", "]", wrapped)   # 去掉末尾多逗号
    wrapped = re.sub(r"\[\s*,", "[", wrapped)   # 去掉开头多逗号
    data = json.loads(wrapped)
    # 只取 dict 且包含 id 的对象
    return [x for x in data if isinstance(x, dict) and "id" in x]


# ---------- 训练 ----------
def train_and_export(
    routes: List[Dict[str, Any]],
    outdir: Path,
    k: int = None,
    auto_k: Optional[Tuple[int, int]] = None,
    random_state: int = 42,
):
    outdir.mkdir(parents=True, exist_ok=True)
    feat = RouteFeatureExtractor(top_k_categories=12)

    # feature
    X = feat.fit_transform(routes)
    scaler = StandardScaler(with_mean=True, with_std=True)

    # 自动选 k（silhouette）或手动指定
    if k is None:
        assert auto_k is not None, "必须指定 k 或 auto_k"
        k_min, k_max = auto_k
        Xs = scaler.fit_transform(X)
        n_samples = Xs.shape[0]
        k_max = min(k_max, max(2, n_samples - 1))
        best_k, best_score, best_model = None, -1.0, None
        for kk in range(max(2, k_min), k_max + 1):
            try:
                model = MiniBatchKMeans(n_clusters=kk, n_init=20, random_state=random_state, batch_size=256)
                labels = model.fit_predict(Xs)
                if len(set(labels)) <= 1 or len(set(labels)) >= n_samples:
                    continue
                s = silhouette_score(Xs, labels)
                if s > best_score:
                    best_k, best_score, best_model = kk, s, model
            except Exception:
                continue
        if best_model is None:
            best_k = min(3, max(2, X.shape[0] - 1))
            best_model = MiniBatchKMeans(n_clusters=best_k, n_init=20, random_state=random_state).fit(Xs)
        model = best_model
        chosen_k = best_k
    else:
        Xs = scaler.fit_transform(X)
        model = KMeans(n_clusters=k, n_init=20, random_state=random_state).fit(Xs)
        chosen_k = k

    pipe: Pipeline = make_pipeline(feat, scaler, model)
    joblib.dump(pipe, outdir / "route_cluster_model.pkl")

    # 预测与导出 JSON
    labels = model.predict(Xs)
    cluster_to_routes = defaultdict(list)
    for r, lbl in zip(routes, labels):
        cluster_to_routes[int(lbl)].append(r)

    themes = []
    for idx, cluster_id in enumerate(sorted(cluster_to_routes.keys())):
        group = cluster_to_routes[cluster_id]
        theme_name = infer_theme_name(group) if group else f"Theme {idx+1}"
        themes.append(
            {"id": f"theme_{idx+1}", "ThemeName": theme_name, "Routes": group}
        )

    out_json = {"themes": themes}
    (outdir / "clustered_routes.json").write_text(json.dumps(out_json, ensure_ascii=False, indent=2), encoding="utf-8")

    # 额外给一个摘要 CSV（方便快看每簇数量）
    summary = pd.DataFrame(
        [{"Theme #": i + 1, "ThemeName": t["ThemeName"], "NumRoutes": len(t["Routes"])} for i, t in enumerate(themes)]
    )
    summary.to_csv(outdir / "cluster_summary.csv", index=False, encoding="utf-8-sig")
    return {"k": chosen_k, "n_routes": len(routes), "outdir": str(outdir)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("data/synthetic_data.jsonl"))
    ap.add_argument("--outdir", type=Path, default=Path("./out"))
    group = ap.add_mutually_exclusive_group(required=False)
    group.add_argument("--k", type=int, help="手动指定聚类个数（= 主题数）")
    group.add_argument("--auto-k", nargs=2, type=int, metavar=("K_MIN", "K_MAX"),
                       help="自动选择 k 的范围（含端点），例如 --auto-k 2 10")
    args = ap.parse_args()

    routes = load_routes_tolerant(args.data)
    if not routes:
        raise RuntimeError(f"没有从 {args.data} 解析到任何 route")

    if args.k is not None:
        info = train_and_export(routes, args.outdir, k=args.k)
    else:
        auto = tuple(args.auto_k) if args.auto_k else (2, 10)
        info = train_and_export(routes, args.outdir, k=None, auto_k=auto)

    print(f"✅ 训练完成：k={info['k']}, routes={info['n_routes']}")
    print(f"📦 模型：{args.outdir / 'route_cluster_model.pkl'}")
    print(f"📄 结果：{args.outdir / 'clustered_routes.json'}")
    print(f"📊 摘要：{args.outdir / 'cluster_summary.csv'}")


if __name__ == "__main__":
    main()
