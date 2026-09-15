"""원본 CSV → Bronze Parquet 변환.

왜 Parquet인가:
  원본은 헤더 없는 3.7GB CSV다. 프로파일링·모델링 단계에서 같은 파일을
  수십 번 재스캔하게 되는데, CSV는 매번 전체 파싱이 필요하다.
  컬럼 지향 포맷으로 한 번 바꿔두면 이후 모든 쿼리가 필요한 컬럼만 읽는다.

멱등성:
  출력 Parquet이 이미 있으면 건너뛴다. --force 로 재생성.
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import duckdb

from . import schema

log = logging.getLogger(__name__)


def convert(
    raw_dir: Path,
    bronze_dir: Path,
    con: duckdb.DuckDBPyConnection,
    force: bool = False,
) -> dict[str, dict[str, float]]:
    """모든 테이블을 Parquet으로 변환하고 테이블별 통계를 돌려준다."""
    bronze_dir.mkdir(parents=True, exist_ok=True)
    stats: dict[str, dict[str, float]] = {}

    for table in schema.TABLES:
        src = raw_dir / f"{table}.csv"
        dst = bronze_dir / f"{table}.parquet"

        if not src.exists():
            raise FileNotFoundError(f"원본 없음: {src} — scripts/fetch_data.sh 먼저 실행")

        if dst.exists() and not force:
            log.info("건너뜀 (이미 존재): %s", dst.name)
        else:
            log.info("변환: %s", table)
            t0 = time.perf_counter()
            con.execute(
                f"COPY (SELECT * FROM {schema.read_csv_sql(table, str(src))}) "
                f"TO '{dst}' (FORMAT parquet, COMPRESSION zstd)"
            )
            log.info("  %.1fs", time.perf_counter() - t0)

        rows = con.execute(f"SELECT count(*) FROM read_parquet('{dst}')").fetchone()[0]
        stats[table] = {
            "rows": rows,
            "csv_mb": src.stat().st_size / 1e6,
            "parquet_mb": dst.stat().st_size / 1e6,
        }

    return stats


def main() -> None:
    p = argparse.ArgumentParser(description="원본 CSV를 Bronze Parquet으로 변환")
    p.add_argument("--raw-dir", type=Path, default=Path("data/raw/alibaba_gpu_2020"))
    p.add_argument("--bronze-dir", type=Path, default=Path("data/bronze/alibaba_gpu_2020"))
    p.add_argument("--force", action="store_true", help="이미 있어도 재생성")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="[to_bronze] %(message)s")
    con = duckdb.connect()
    stats = convert(args.raw_dir, args.bronze_dir, con, force=args.force)

    print(f"\n{'table':<24}{'rows':>14}{'csv MB':>10}{'parquet MB':>12}{'압축률':>9}")
    for t, s in stats.items():
        ratio = s["parquet_mb"] / s["csv_mb"] if s["csv_mb"] else 0
        print(f"{t:<24}{int(s['rows']):>14,}{s['csv_mb']:>10.0f}{s['parquet_mb']:>12.0f}{ratio:>8.1%}")


if __name__ == "__main__":
    main()
