from __future__ import annotations

import datetime as dt
from pathlib import Path

from .common import load_raw_excel, normalize_holdings_df


def parse_koact_holdings(path: str | Path, *, date: dt.date) -> "pd.DataFrame":
    """
    KoAct 코스닥액티브 구성종목 엑셀을 파싱해 공통 스키마 DataFrame으로 반환한다.

    NOTE: 엑셀 포맷이 변경되면 `etl/common.py`의 컬럼 후보 목록을 조정하면 된다.
    """
    import pandas as pd  # 지연 로딩

    p = Path(path)
    raw_df = load_raw_excel(p)
    # KoAct 엑셀은 비중을 0.0074(=0.74%)처럼 소수로 제공하므로 100배 스케일링
    df = normalize_holdings_df(
        raw_df, etf_slug="koact", date=date, weight_scale=100.0
    )
    # 원화예금 등 현금성 항목은 추적 대상에서 제외
    mask_not_cash_name = ~df["name"].str.contains("원화예금", na=False)
    return df[mask_not_cash_name].reset_index(drop=True)


__all__ = ["parse_koact_holdings"]

