from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


@dataclass
class Holding:
    ticker: str
    name: str
    shares: float
    market_value: float
    weight: float
    cash_flag: bool
    etf: str
    date: dt.date


COLUMN_CANDIDATES = {
    "ticker": ["종목코드", "코드"],
    "name": ["종목명", "명"],
    "shares": ["수량"],
    "market_value": ["평가금액", "평가 금액"],
    "weight": ["비중"],
}


def _choose_column(columns: Iterable[str], candidates: list[str]) -> str:
    lowered = {str(c).strip(): str(c).strip().lower() for c in columns}
    for cand in candidates:
        cand_lower = cand.lower()
        for original, low in lowered.items():
            if cand_lower in low:
                return original
    raise KeyError(f"컬럼을 찾을 수 없습니다: {candidates}")


def _find_header_row(raw: pd.DataFrame) -> int:
    """
    '종목코드'와 '종목명'이 포함된 행을 헤더로 간주한다.
    """
    for idx, row in raw.iterrows():
        values = [str(v) for v in row.tolist()]
        if any("종목코드" in v for v in values) and any("종목명" in v for v in values):
            return idx
    # 기본값: 첫 번째 행
    return 0


def load_raw_excel(path: Path) -> pd.DataFrame:
    """
    엑셀 파일을 읽어 DataFrame(raw)을 반환한다.

    기본적으로 openpyxl로 시도하고, 실패 시 pandas 기본 엔진으로 한 번 더 시도한다.
    (pandas / xlrd 버전 변화에 따른 호환성 문제를 최소화하기 위함)
    """
    try:
        raw = pd.read_excel(path, header=None, engine="openpyxl")
    except Exception:
        # openpyxl로 읽지 못하는 특수 포맷일 경우, 엔진을 지정하지 않고 재시도
        raw = pd.read_excel(path, header=None)
    header_row = _find_header_row(raw)
    header = raw.iloc[header_row].tolist()
    df = raw.iloc[header_row + 1 :].copy()
    df.columns = header
    return df


def normalize_holdings_df(
    df: pd.DataFrame,
    *,
    etf_slug: str,
    date: dt.date,
    weight_scale: float = 1.0,
) -> pd.DataFrame:
    """
    ETF 보유 종목 DataFrame을 공통 스키마로 변환한다.
    """
    cols = df.columns.tolist()
    ticker_col = _choose_column(cols, COLUMN_CANDIDATES["ticker"])
    name_col = _choose_column(cols, COLUMN_CANDIDATES["name"])
    shares_col = _choose_column(cols, COLUMN_CANDIDATES["shares"])
    mv_col = _choose_column(cols, COLUMN_CANDIDATES["market_value"])
    weight_col = _choose_column(cols, COLUMN_CANDIDATES["weight"])

    out = pd.DataFrame(
        {
            "ticker": df[ticker_col].astype(str).str.strip(),
            "name": df[name_col].astype(str).str.strip(),
            "shares": pd.to_numeric(df[shares_col], errors="coerce"),
            "market_value": pd.to_numeric(df[mv_col], errors="coerce"),
            "weight": pd.to_numeric(df[weight_col], errors="coerce"),
        }
    )

    # 불필요 행 제거 (현금, 합계, 공백 등)
    mask_valid_ticker = out["ticker"].notna() & (out["ticker"] != "")  # type: ignore[operator]
    mask_not_cash = ~out["ticker"].str.contains("현금|합계", na=False)
    out = out[mask_valid_ticker & mask_not_cash].copy()

    # ETF별 표현 방식 차이를 보정하기 위해 비중 스케일 조정
    if weight_scale != 1.0:
        out["weight"] = out["weight"] * weight_scale

    out["cash_flag"] = False
    out["etf"] = etf_slug.upper()
    out["date"] = date

    # 인덱스 정리
    out.reset_index(drop=True, inplace=True)
    return out

