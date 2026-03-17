from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from textwrap import shorten

import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv()


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def _fmt_qty(x: object) -> str:
    try:
        v = float(x)
    except Exception:
        return "0"
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.4f}"


class TelegramConfigError(RuntimeError):
    pass


def _ensure_telegram_config() -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise TelegramConfigError(
            "TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID 환경 변수가 설정되지 않았습니다."
        )


def send_telegram_message(text: str, *, parse_mode: str | None = None) -> None:
    """
    텔레그램 채팅으로 단순 텍스트 메시지를 전송한다.
    """
    _ensure_telegram_config()
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload: dict[str, str] = {
        "chat_id": TELEGRAM_CHAT_ID,  # type: ignore[arg-type]
        "text": text,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    resp = requests.post(url, data=payload, timeout=10)
    resp.raise_for_status()


def send_telegram_document(file_path: Path, *, caption: str | None = None) -> None:
    """
    텔레그램 채팅으로 파일(문서)을 전송한다. 전체 diff CSV 등을 첨부할 때 사용.
    """
    _ensure_telegram_config()
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    with open(file_path, "rb") as f:
        payload: dict = {"chat_id": TELEGRAM_CHAT_ID}
        if caption:
            payload["caption"] = caption
        resp = requests.post(
            url, data=payload, files={"document": (file_path.name, f)}, timeout=30
        )
    resp.raise_for_status()


def send_telegram_long_message(text: str, *, parse_mode: str | None = None) -> None:
    """
    텔레그램은 메시지 길이 제한(약 4096자)이 있어, 긴 메시지는 여러 번 나누어 전송한다.
    """
    max_len = 3500  # 여유 버퍼를 두고 분할
    lines = text.split("\n")
    buf: list[str] = []

    def flush() -> None:
        if not buf:
            return
        chunk = "\n".join(buf)
        send_telegram_message(chunk, parse_mode=parse_mode)
        buf.clear()

    for line in lines:
        # 다음 줄을 붙였을 때 길이가 너무 길어지면 먼저 전송
        tentative = ("\n".join(buf + [line])) if buf else line
        if len(tentative) > max_len:
            flush()
            buf.append(line)
        else:
            buf.append(line)

    flush()


def _format_section(title: str, df: pd.DataFrame, *, max_rows: int = 0) -> str:
    if df.empty:
        return f"{title}\n(변동 없음)\n"

    lines: list[str] = [title]
    # max_rows <= 0 이면 전체, 양수면 상위 max_rows 개만
    subset = df if max_rows <= 0 else df.head(max_rows)

    for _, row in subset.iterrows():
        name = str(row.get("name", ""))
        ticker = str(row.get("ticker", ""))
        s_prev = row.get("shares_prev", 0.0)
        s_curr = row.get("shares_curr", 0.0)
        s_chg = row.get("shares_change", 0.0)
        w_curr = float(row.get("weight_curr", 0.0))
        name_short = shorten(name, width=18, placeholder="…")
        lines.append(
            f"- {name_short}({ticker}): {_fmt_qty(s_prev)} → {_fmt_qty(s_curr)} "
            f"(Δ {float(s_chg):+.0f}) [{w_curr:.2f}%]"
        )
    return "\n".join(lines) + "\n"


def build_diff_message(
    *,
    etf_name: str,
    date: dt.date,
    diff,
    top_n: int = 10,
    prev_date: dt.date | None = None,
) -> str:
    """
    diff 결과(DataFrame 묶음)를 사람이 읽기 좋은 메시지로 변환한다.
    prev_date: 비교 기준일(이전 거래일). 있으면 메시지에 표시한다.
    """
    new_df = diff["new_entries"]
    removed_df = diff["removed"]
    increased_df = diff["increased"]
    decreased_df = diff["decreased"]

    header = f"[{etf_name}] {date.isoformat()} 구성종목 변화 요약"
    parts = [header, ""]
    if prev_date is not None:
        parts.append(f"비교 기준: {prev_date.isoformat()} → {date.isoformat()}")
        parts.append("")

    parts.extend([
        _format_section("신규 편입", new_df, max_rows=0),
        _format_section("편출 종목", removed_df, max_rows=0),
        _format_section("수량 증가", increased_df, max_rows=0),
        _format_section("수량 감소", decreased_df, max_rows=0),
    ])

    return "\n".join(parts).strip()


def build_snapshot_message(
    *,
    etf_name: str,
    date: dt.date,
    holdings: pd.DataFrame,
    top_n: int = 10,
) -> str:
    """
    전일 데이터가 없을 때, 현재 보유 상위 종목 스냅샷을 보내기 위한 메시지.
    """
    header = f"[{etf_name}] {date.isoformat()} 기준 구성종목 스냅샷"

    if holdings.empty:
        return header + "\n(보유 종목이 없습니다.)"

    subset = (
        holdings.sort_values("shares", ascending=False)
        if top_n <= 0
        else holdings.sort_values("shares", ascending=False).head(top_n)
    )
    lines = [header, ""]
    lines.append("상위 보유 종목:")
    for _, row in subset.iterrows():
        name = str(row.get("name", ""))
        ticker = str(row.get("ticker", ""))
        s = row.get("shares", 0.0)
        w = float(row.get("weight", 0.0))
        name_short = shorten(name, width=18, placeholder="…")
        lines.append(f"- {name_short}({ticker}): {_fmt_qty(s)} [{w:.2f}%]")

    lines.append("")
    lines.append("※ 전일 데이터가 없어 변화율은 내일부터 계산됩니다.")
    return "\n".join(lines).strip()


__all__ = [
    "TelegramConfigError",
    "send_telegram_message",
    "send_telegram_long_message",
    "send_telegram_document",
    "build_diff_message",
    "build_snapshot_message",
]

