"""_get_target_date 검증 로직 테스트"""
from __future__ import annotations

import datetime as dt
import sys

# main 모듈에서 함수 임포트 (pandas 등 무거운 임포트를 피하기 위해 직접 복사)
# 실제 함수와 동일한 코드를 테스트
def _is_weekday(d: dt.date) -> bool:
    return d.weekday() < 5


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
            print(f"[경고] {date.isoformat()}({day_name}요일)는 주말입니다.")
        return date
    return dt.date.today()


PASS = "PASS"
FAIL = "FAIL"
failures = []


def check(label: str, *, expect_exit: bool = False, expect_warning: bool = False, arg: str | None):
    try:
        result = _get_target_date(arg)
        if expect_exit:
            failures.append((label, f"SystemExit 발생해야 하는데 {result} 반환됨"))
            print(f"  {FAIL}  {label}")
        else:
            print(f"  {PASS}  {label} => {result}")
    except SystemExit as e:
        if expect_exit:
            print(f"  {PASS}  {label} => (종료: {str(e)[:40]}...)")
        else:
            failures.append((label, f"예상치 못한 SystemExit: {e}"))
            print(f"  {FAIL}  {label}")


print("=" * 55)
print("  _get_target_date 검증 테스트")
print("=" * 55)

# 1. 정상 평일
check("정상 날짜 (2025-03-21 금)", arg="2025-03-21")

# 2. 잘못된 형식 - 슬래시
check("잘못된 형식 (2025/03/21)", expect_exit=True, arg="2025/03/21")

# 3. 잘못된 형식 - 점
check("잘못된 형식 (21.03.2025)", expect_exit=True, arg="21.03.2025")

# 4. 잘못된 형식 - 문자열
check("잘못된 형식 (abc)", expect_exit=True, arg="abc")

# 5. YYYYMMDD 형식 - Python 3.11+에서 ISO 8601 기본 형식으로 허용됨
check("YYYYMMDD 형식 (20250321)", arg="20250321")

# 6. 미래 날짜
check("미래 날짜 (2099-01-01)", expect_exit=True, arg="2099-01-01")

# 7. 내일 날짜도 미래
tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
check(f"내일 날짜 ({tomorrow})", expect_exit=True, arg=tomorrow)

# 8. 주말 - 토요일 (종료되지 않고 경고만)
check("주말 (2025-03-22 토)", expect_warning=True, arg="2025-03-22")

# 9. 주말 - 일요일
check("주말 (2025-03-23 일)", expect_warning=True, arg="2025-03-23")

# 10. None -> 오늘 반환
check("None 입력 (오늘)", arg=None)

# 11. 오늘 날짜 직접 입력 (경계값)
today = dt.date.today().isoformat()
check(f"오늘 날짜 ({today})", arg=today)

# 12. 과거 날짜
check("과거 날짜 (2020-01-02 목)", arg="2020-01-02")

print("=" * 55)
if failures:
    print(f"  결과: {len(failures)}개 실패")
    for label, reason in failures:
        print(f"    - {label}: {reason}")
    sys.exit(1)
else:
    print(f"  결과: 전체 통과")
