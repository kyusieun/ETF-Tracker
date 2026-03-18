from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

import requests

from etf_tracker.config import PLUS150


logger = logging.getLogger(__name__)


PLUS150_DOWNLOAD_URL = (
    "https://www.plusetf.co.kr/excel/product/pdf?"
    "&n=006399&d={yyyymmdd}&title=PLUS%20%EC%BD%94%EC%8A%A4%EB%8B%A5150%EC%95%A1%ED%8B%B0%EB%B8%8C"
)


def download_plus150_excel(date: dt.date) -> Path | None:
    """
    주어진 날짜의 PLUS 코스닥150액티브 구성종목 엑셀을 다운로드해 data/plus150/ 에 저장한다.

    - 이미 같은 날짜 파일이 있으면 다운로드를 건너뛴다.
    - 성공 시 저장된 파일 경로를, 실패 시 None을 반환한다.
    """
    data_dir = PLUS150.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{date.isoformat()}_plus150.xlsx"
    dest_path = data_dir / filename
    if dest_path.exists():
        logger.info("PLUS150 엑셀 파일이 이미 존재합니다: %s", dest_path)
        return dest_path

    yyyymmdd = date.strftime("%Y%m%d")
    url = PLUS150_DOWNLOAD_URL.format(yyyymmdd=yyyymmdd)
    logger.info("PLUS150 엑셀 다운로드 시도: url=%s", url)

    headers = {
        # 일부 사이트는 User-Agent/Referer 없으면 파일 다운로드를 차단한다.
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.plusetf.co.kr/product/detail?n=006399",
    }

    try:
        resp = requests.get(url, timeout=30, headers=headers)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logger.error("PLUS150 엑셀 다운로드 실패: %s", exc)
        return None

    # 간단 검증: 내용이 너무 짧으면 (에러 페이지 등) 실패로 간주
    if len(resp.content) < 1024:
        logger.error("PLUS150 엑셀 응답이 비정상적으로 짧습니다. (size=%d)", len(resp.content))
        return None

    dest_path.write_bytes(resp.content)
    logger.info("PLUS150 엑셀 다운로드 완료: %s", dest_path)
    return dest_path


__all__ = ["download_plus150_excel"]

