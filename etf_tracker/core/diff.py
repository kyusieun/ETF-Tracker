from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal, TypedDict

import pandas as pd


class DiffResult(TypedDict):
    full: pd.DataFrame
    new_entries: pd.DataFrame
    removed: pd.DataFrame
    increased: pd.DataFrame
    decreased: pd.DataFrame


@dataclass
class DiffConfig:
    top_n: int = 10
    shares_epsilon: float = 1.0  # |Δ수량|이 이 값 미만이면 변화 없음으로 간주


def _prepare(
    prev_df: pd.DataFrame,
    curr_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    전일/금일 DataFrame을 합쳐 변화량 컬럼을 계산한 전체 테이블을 만든다.
    """
    on_cols = ["ticker"]
    merged = prev_df.merge(
        curr_df,
        on=on_cols,
        how="outer",
        suffixes=("_prev", "_curr"),
        indicator=True,
    )

    for col in ["shares", "weight"]:
        merged[f"{col}_prev"] = merged[f"{col}_prev"].fillna(0.0)
        merged[f"{col}_curr"] = merged[f"{col}_curr"].fillna(0.0)
        merged[f"{col}_change"] = merged[f"{col}_curr"] - merged[f"{col}_prev"]

    merged["weight_change_bp"] = merged["weight_change"] * 100  # % → bp

    # 이름/기타 컬럼 정리 (가능하면 금일 기준, 없으면 전일 기준)
    merged["name"] = merged["name_curr"].combine_first(merged["name_prev"])

    return merged


def compute_diff(
    prev_df: pd.DataFrame,
    curr_df: pd.DataFrame,
    *,
    config: DiffConfig | None = None,
) -> DiffResult:
    """
    전일/금일 보유 종목 DataFrame 간의 변화를 계산한다.
    """
    if config is None:
        config = DiffConfig()

    merged = _prepare(prev_df, curr_df)
    eps = float(config.shares_epsilon)

    # 신규 편입 / 편출
    new_entries = merged[merged["_merge"] == "right_only"].copy()
    removed = merged[merged["_merge"] == "left_only"].copy()

    # 계속 보유 중이면서 수량 변화가 있는 종목 (|Δ수량| < eps 는 제외)
    common = merged[merged["_merge"] == "both"].copy()
    common = common[common["shares_change"].abs() >= eps].copy()

    increased = common[common["shares_change"] > 0].copy()
    increased["abs_shares_change"] = increased["shares_change"].abs()
    increased = increased.sort_values("abs_shares_change", ascending=False).drop(
        columns=["abs_shares_change"]
    )

    decreased = common[common["shares_change"] < 0].copy()
    decreased["abs_shares_change"] = decreased["shares_change"].abs()
    decreased = decreased.sort_values("abs_shares_change", ascending=False).drop(
        columns=["abs_shares_change"]
    )

    return {
        "full": merged,
        "new_entries": new_entries,
        "removed": removed,
        "increased": increased,
        "decreased": decreased,
    }


__all__ = ["DiffResult", "DiffConfig", "compute_diff"]

