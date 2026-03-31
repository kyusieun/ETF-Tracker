from __future__ import annotations

import datetime as dt
from pathlib import Path

from .common import load_raw_excel, normalize_holdings_df


def parse_time_kospi_holdings(path: str | Path, *, date: dt.date) -> "pd.DataFrame":
    """
    TIME 코스피액티브 구성종목 엑셀을 파싱해 공통 스키마 DataFrame으로 반환한다.
    """
    import pandas as pd  # 지연 로딩

    p = Path(path)
    raw_df = load_raw_excel(p)
    return normalize_holdings_df(raw_df, etf_slug="timek", date=date)


__all__ = ["parse_time_kospi_holdings"]
