from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class EtfConfig:
    code: str
    name: str
    slug: str  # 디렉터리/CLI에서 사용할 짧은 이름
    data_dir: Path
    download_url: str | None = None  # 필요 시 사용자 수정


DATA_DIR = BASE_DIR / "data"

KOACT = EtfConfig(
    code="2ETFU6",
    name="KoAct 코스닥액티브",
    slug="koact",
    data_dir=DATA_DIR / "koact",
    # TODO: 실제 엑셀 다운로드 URL을 확인한 후 업데이트
    download_url=None,
)

TIME = EtfConfig(
    code="0162Y0",
    name="TIME 코스닥 액티브",
    slug="time",
    data_dir=DATA_DIR / "time",
    # TODO: 실제 엑셀 다운로드 URL을 확인한 후 업데이트
    download_url=None,
)

PLUS150 = EtfConfig(
    code="006399",
    name="PLUS 코스닥150액티브",
    slug="plus150",
    data_dir=DATA_DIR / "plus150",
    download_url=None,
)

TIME_KOSPI = EtfConfig(
    code="385720",
    name="TIME 코스피액티브",
    slug="timek",
    data_dir=DATA_DIR / "timek",
    download_url=None,
)


ETF_BY_SLUG = {
    KOACT.slug: KOACT,
    TIME.slug: TIME,
    PLUS150.slug: PLUS150,
    TIME_KOSPI.slug: TIME_KOSPI,
}


def get_etf_config(slug: str) -> EtfConfig:
    try:
        return ETF_BY_SLUG[slug]
    except KeyError as exc:
        raise ValueError(f"지원하지 않는 ETF 식별자입니다: {slug}") from exc

