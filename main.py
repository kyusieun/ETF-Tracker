from __future__ import annotations

import argparse
import datetime as dt
import logging
from pathlib import Path

import pandas as pd

from etf_tracker.config import KOACT, PLUS150, TIME, EtfConfig, get_etf_config
from etf_tracker.core.diff import DiffConfig, compute_diff
from etf_tracker.alerts.telegram import (
    TelegramConfigError,
    build_diff_message,
    build_snapshot_message,
    send_telegram_document,
    send_telegram_long_message,
)
from etf_tracker.etl.koact import parse_koact_holdings
from etf_tracker.etl.plus150 import parse_plus150_holdings
from etf_tracker.etl.time_etf import parse_time_holdings
from etf_tracker.etl.koact_download import download_koact_excel
from etf_tracker.etl.plus150_download import download_plus150_excel
from etf_tracker.etl.time_download import download_time_excel


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KoAct / TIME ETF 트래커")
    parser.add_argument(
        "--date",
        type=str,
        help="대상 일자 (YYYY-MM-DD), 기본: 오늘",
    )
    parser.add_argument(
        "--etf",
        choices=["koact", "time", "plus150"],
        action="append",
        help="대상 ETF(여러 번 지정 가능). 예: --etf koact --etf time",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="지원 ETF 모두 실행",
    )
    return parser.parse_args()


def _get_target_date(arg_date: str | None) -> dt.date:
    if arg_date:
        try:
            date = dt.date.fromisoformat(arg_date)
        except ValueError:
            raise SystemExit(
                f"[오류] 날짜 형식이 올바르지 않습니다: '{arg_date}'\n"
                "       YYYY-MM-DD 형식으로 입력해 주세요. 예: 2025-03-21"
            )
        if date > dt.date.today():
            raise SystemExit(
                f"[오류] 미래 날짜는 사용할 수 없습니다: {date.isoformat()}\n"
                f"       오늘 날짜 이하로 입력해 주세요. (오늘: {dt.date.today().isoformat()})"
            )
        if not _is_weekday(date):
            day_name = ["월", "화", "수", "목", "금", "토", "일"][date.weekday()]
            logger.warning(
                "입력한 날짜 %s(%s요일)는 주말입니다. 데이터가 없을 수 있습니다.",
                date.isoformat(),
                day_name,
            )
        return date
    return dt.date.today()


def _is_weekday(d: dt.date) -> bool:
    """월요일(0)~금요일(4)만 True. 토(5), 일(6)은 False."""
    return d.weekday() < 5


def _iter_previous_dates(date: dt.date, *, max_days: int = 14):
    """대상일 이전 날짜를 하루씩 거꾸로 나열. 주말은 제외하고 평일만 yield."""
    count = 0
    for i in range(1, max_days + 1):
        if count >= 10:
            break
        cand = date - dt.timedelta(days=i)
        if not _is_weekday(cand):
            continue
        count += 1
        yield cand


def _find_file_for_date(etf: EtfConfig, date: dt.date) -> Path | None:
    """
    data/<etf>/ 디렉터리에서 주어진 날짜에 해당하는 파일을 찾는다.
    우선순위:
    1) YYYY-MM-DD.* 패턴
    2) 파일명 안에 YYYYMMDD 문자열이 포함된 경우
    """
    if not etf.data_dir.exists():
        return None

    ymd_dash = date.isoformat()  # YYYY-MM-DD
    ymd_compact = date.strftime("%Y%m%d")

    candidates: list[Path] = []
    for path in etf.data_dir.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".xls", ".xlsx"}:
            continue
        name = path.name
        if ymd_dash in name or ymd_compact in name:
            candidates.append(path)

    if candidates:
        # 가장 최근 수정된 파일 하나 선택
        return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]

    # 정확한 패턴이 없으면 YYYY-MM-DD.* 이름을 기본으로 가정
    for ext in (".xlsx", ".xls"):
        guess = etf.data_dir / f"{ymd_dash}{ext}"
        if guess.exists():
            return guess

    return None


# 이전 거래일로 인정할 최소 보유 종목 수 (휴일/주말에 빈 파일이 오는 경우 필터링)
MIN_HOLDINGS_PREV_DAY = 10


def _find_previous_file(etf: EtfConfig, date: dt.date) -> tuple[Path | None, dt.date | None]:
    """
    최근 이전 평일만 후보로 두고, 자료가 있는 가장 최근 이전 거래일을 찾는다.
    주말(토·일)은 후보에서 제외하며, 각 후보 날짜에 대해 웹에서 엑셀 다운로드 후
    파일이 실제로 충분한 보유 종목을 담고 있는지 검사한다.
    반환: (이전일 파일 경로, 이전일 날짜). 없으면 (None, None).
    """
    for prev_date in _iter_previous_dates(date, max_days=14):
        try:
            if etf.slug == "koact":
                download_koact_excel(prev_date)
            elif etf.slug == "time":
                download_time_excel(prev_date)
            elif etf.slug == "plus150":
                download_plus150_excel(prev_date)
        except Exception as exc:  # noqa: BLE001
            logger.debug("이전일 자동 다운로드 실패(무시하고 계속): %s", exc)
        prev_path = _find_file_for_date(etf, prev_date)
        if prev_path is None:
            continue
        try:
            prev_df = _load_holdings(etf, prev_path, prev_date)
            if len(prev_df) < MIN_HOLDINGS_PREV_DAY:
                logger.info(
                    "이전일 후보 %s: 보유 종목 수 부족(%d) → 건너뜀",
                    prev_date.isoformat(),
                    len(prev_df),
                )
                continue
        except Exception as exc:  # noqa: BLE001
            logger.debug("이전일 파일 파싱 실패(건너뜀): %s", exc)
            continue
        logger.info("이전 거래일로 사용: %s (날짜 %s)", prev_path.name, prev_date.isoformat())
        return (prev_path, prev_date)
    return (None, None)


def _load_holdings(etf: EtfConfig, path: Path, date: dt.date) -> pd.DataFrame:
    if etf.slug == "koact":
        return parse_koact_holdings(path, date=date)
    if etf.slug == "time":
        return parse_time_holdings(path, date=date)
    if etf.slug == "plus150":
        return parse_plus150_holdings(path, date=date)
    raise ValueError(f"알 수 없는 ETF slug: {etf.slug}")


def process_etf(etf: EtfConfig, date: dt.date) -> None:
    logger.info("=== %s (%s) 처리 시작: %s ===", etf.name, etf.slug, date)

    etf.data_dir.mkdir(parents=True, exist_ok=True)

    # 1) 우선 웹에서 해당 날짜 엑셀을 다운로드 시도 (이미 있으면 내부에서 스킵)
    try:
        if etf.slug == "koact":
            download_koact_excel(date)
        elif etf.slug == "time":
            download_time_excel(date)
        elif etf.slug == "plus150":
            download_plus150_excel(date)
    except Exception as exc:  # noqa: BLE001
        logger.error("엑셀 자동 다운로드 중 오류 (ETF=%s, date=%s): %s", etf.slug, date, exc)

    # 2) 로컬 data/<etf>/ 에서 파일 검색
    curr_path = _find_file_for_date(etf, date)
    if curr_path is None:
        logger.error(
            "대상 일자 파일을 찾을 수 없습니다. data/%s/ 폴더에 파일명을 날짜가 포함되도록 옮겨 주세요. (예: %s-.. .xlsx)",
            etf.slug,
            date.isoformat(),
        )
        return

    curr_df = _load_holdings(etf, curr_path, date)

    # 보호 로직(보수적): PLUS150은 상장 초기/휴장일/데이터 미제공 시에도 파일이 내려올 수 있어
    # 보유 종목이 비정상적으로 적으면(기본 10개 미만) 비교/이전일 탐색을 진행하지 않는다.
    if etf.slug == "plus150" and len(curr_df) < MIN_HOLDINGS_PREV_DAY:
        logger.warning(
            "현재일 데이터가 비정상적으로 적어 비교를 생략합니다. (ETF=%s, date=%s, holdings=%d)",
            etf.slug,
            date,
            len(curr_df),
        )
        try:
            message = build_snapshot_message(
                etf_name=etf.name,
                date=date,
                holdings=curr_df,
                top_n=0,
                note="비교 기준: (현재일 데이터 부족으로 비교 생략)",
            )
            send_telegram_long_message(message)
            logger.info("텔레그램 스냅샷(비교 생략) 전송 완료")
        except TelegramConfigError as e:
            logger.error("텔레그램 설정 오류: %s", e)
        except Exception as e:  # noqa: BLE001
            logger.exception("텔레그램 스냅샷 전송 중 오류 발생: %s", e)
        return

    prev_path, prev_date = _find_previous_file(etf, date)
    if prev_path is None or prev_date is None:
        logger.warning(
            "이전 거래일 파일이 없어 기준 스냅샷만 전송합니다. (ETF=%s, date=%s)",
            etf.slug,
            date,
        )
        try:
            message = build_snapshot_message(
                etf_name=etf.name,
                date=date,
                holdings=curr_df,
                top_n=0,
                note="비교 기준: (이전 거래일 데이터 없음)",
            )
            send_telegram_long_message(message)
            logger.info("텔레그램 스냅샷 알림 전송 완료")
        except TelegramConfigError as e:
            logger.error("텔레그램 설정 오류: %s", e)
        except Exception as e:  # noqa: BLE001
            logger.exception("텔레그램 스냅샷 전송 중 오류 발생: %s", e)
        return

    prev_df = _load_holdings(etf, prev_path, prev_date)

    diff = compute_diff(prev_df, curr_df, config=DiffConfig(top_n=10))

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    full_out = reports_dir / f"{etf.slug}_{date.isoformat()}_full.csv"
    # CSV에는 핵심 컬럼만 남긴다.
    full_df = diff["full"].copy()
    desired_cols = [
        "ticker",
        "name",
        "shares_prev",
        "shares_curr",
        "weight_prev",
        "weight_curr",
    ]
    existing_cols = [c for c in desired_cols if c in full_df.columns]
    full_df = full_df[existing_cols]
    full_df.to_csv(full_out, index=False, encoding="utf-8-sig")
    logger.info("full diff CSV 저장: %s", full_out)

    # 텔레그램 알림 (요약 메시지 + 전체 CSV 첨부)
    try:
        message = build_diff_message(
            etf_name=etf.name,
            date=date,
            diff=diff,
            top_n=0,
            prev_date=prev_date,
        )
        send_telegram_long_message(message)
        send_telegram_document(
            full_out,
            caption=f"{etf.name} {date.isoformat()} 전체 diff (비교 기준: {prev_date.isoformat()} → {date.isoformat()})",
        )
        logger.info("텔레그램 알림 및 전체 파일 전송 완료")
    except TelegramConfigError as e:
        logger.error("텔레그램 설정 오류: %s", e)
    except Exception as e:  # noqa: BLE001
        logger.exception("텔레그램 전송 중 오류 발생: %s", e)


def main() -> None:
    args = _parse_args()
    date = _get_target_date(args.date)

    if args.all or not args.etf:
        targets = [KOACT, TIME, PLUS150]
    else:
        targets = [get_etf_config(slug) for slug in args.etf]

    for etf in targets:
        process_etf(etf, date)


if __name__ == "__main__":
    main()

