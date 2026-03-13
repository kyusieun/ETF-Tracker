from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

import requests

from etf_tracker.config import TIME


logger = logging.getLogger(__name__)


TIME_DOWNLOAD_URL = (
    "https://timeetf.co.kr/pdf_excel.php?idx=24&cate=&pdfDate={ymd_dash}&"
)


def download_time_excel(date: dt.date) -> Path | None:
    """
    주어진 날짜의 TIME 코스닥 액티브 구성종목 엑셀을 다운로드해 data/time/ 에 저장한다.

    - 이미 같은 날짜 파일이 있으면 다운로드를 건너뛴다.
    - 성공 시 저장된 파일 경로를, 실패 시 None을 반환한다.
    """
    data_dir = TIME.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    # 파일명: YYYY-MM-DD_time.xlsx
    filename = f"{date.isoformat()}_time.xlsx"
    dest_path = data_dir / filename

    if dest_path.exists():
        logger.info("TIME 엑셀 파일이 이미 존재합니다: %s", dest_path)
        return dest_path

    ymd_dash = date.strftime("%Y-%m-%d")
    url = TIME_DOWNLOAD_URL.format(ymd_dash=ymd_dash)
    logger.info("TIME 엑셀 다운로드 시도: url=%s", url)

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logger.error("TIME 엑셀 다운로드 실패: %s", exc)
        return None

    # 간단 검증: 내용이 너무 짧으면 (에러 페이지 등) 실패로 간주
    if len(resp.content) < 1024:
        logger.error("TIME 엑셀 응답이 비정상적으로 짧습니다. (size=%d)", len(resp.content))
        return None

    dest_path.write_bytes(resp.content)
    logger.info("TIME 엑셀 다운로드 완료: %s", dest_path)
    return dest_path


__all__ = ["download_time_excel"]

