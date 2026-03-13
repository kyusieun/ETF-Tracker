from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

import requests

from etf_tracker.config import KOACT


logger = logging.getLogger(__name__)


KOACT_DOWNLOAD_URL = (
    "https://www.samsungactive.co.kr/excel_pdf.do?fId=2ETFU6&gijunYMD={ymd}"
)


def download_koact_excel(date: dt.date) -> Path | None:
    """
    주어진 날짜의 KoAct 코스닥액티브 구성종목 엑셀을 다운로드해 data/koact/ 에 저장한다.

    - 이미 같은 날짜 파일이 있으면 다운로드를 건너뛴다.
    - 성공 시 저장된 파일 경로를, 실패 시 None을 반환한다.
    """
    data_dir = KOACT.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    # 파일명: YYYY-MM-DD_koact.xls (main.py의 _find_file_for_date는 날짜 문자열만 있으면 된다)
    filename = f"{date.isoformat()}_koact.xls"
    dest_path = data_dir / filename

    if dest_path.exists():
        logger.info("KoAct 엑셀 파일이 이미 존재합니다: %s", dest_path)
        return dest_path

    ymd = date.strftime("%Y%m%d")
    url = KOACT_DOWNLOAD_URL.format(ymd=ymd)
    logger.info("KoAct 엑셀 다운로드 시도: url=%s", url)

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logger.error("KoAct 엑셀 다운로드 실패: %s", exc)
        return None

    # 간단 검증: 내용이 너무 짧으면 (에러 페이지 등) 실패로 간주
    if len(resp.content) < 1024:
        logger.error("KoAct 엑셀 응답이 비정상적으로 짧습니다. (size=%d)", len(resp.content))
        return None

    dest_path.write_bytes(resp.content)
    logger.info("KoAct 엑셀 다운로드 완료: %s", dest_path)
    return dest_path


__all__ = ["download_koact_excel"]

