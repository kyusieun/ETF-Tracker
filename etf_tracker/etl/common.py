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


def _choose_column_optional(columns: Iterable[str], candidates: list[str]) -> str | None:
    try:
        return _choose_column(columns, candidates)
    except KeyError:
        return None


def _clean_numeric(series: "pd.Series") -> "pd.Series":
    """
    숫자 컬럼으로 변환하기 전 문자열 정리.
    - %, 콤마, 공백 등 제거
    """
    s = series.astype(str).str.strip()
    s = s.str.replace(",", "", regex=False)
    s = s.str.replace("%", "", regex=False)
    return pd.to_numeric(s, errors="coerce")


def _normalize_ticker_value(v: object) -> str:
    """
    종목코드 정규화.
    - 숫자만 있는 경우: 6자리로 zero-pad
    - 393890.0 같은 형태: 소수점 제거 후 처리
    - 0009K0 같은 영문 포함 코드는 원형 유지(공백만 제거)
    """
    s = str(v).strip()
    if s == "" or s.lower() == "nan":
        return ""

    # Excel이 숫자로 읽어 float 문자열(예: 393890.0)로 들어오는 케이스
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]

    if s.isdigit():
        return s.zfill(6)

    # 영문/기호 포함이면 원형 유지 (다만 내부 공백은 제거)
    return s.replace(" ", "")


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
    mv_col = _choose_column_optional(cols, COLUMN_CANDIDATES["market_value"])
    weight_col = _choose_column(cols, COLUMN_CANDIDATES["weight"])

    ticker_series = df[ticker_col].map(_normalize_ticker_value)

    # 평가금액 컬럼은 일부 ETF(예: PLUS)에는 없을 수 있다.
    if mv_col is None:
        market_value_series = pd.Series([pd.NA] * len(df), index=df.index)
    else:
        market_value_series = _clean_numeric(df[mv_col])

    out = pd.DataFrame(
        {
            "ticker": ticker_series,
            "name": df[name_col].astype(str).str.strip(),
            "shares": _clean_numeric(df[shares_col]),
            "market_value": market_value_series,
            "weight": _clean_numeric(df[weight_col]),
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

