"""Bronze Parquet 프로파일링 → docs/04-data-profile.md 생성.

Week 1 의 목적은 "데이터가 실제로 어떻게 생겼는지" 확정하는 것이다.
문서에 적힌 스펙과 실제 파일은 자주 다르다.

재현:
    PYTHONPATH=src python3 -m gpu_finops.ingest.profile_raw
"""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import duckdb

BRONZE_DEFAULT = Path("data/bronze/alibaba_gpu_2020")
OUT_DEFAULT = Path("docs/04-data-profile.md")

VIEWS = [
    "pai_job_table", "pai_task_table", "pai_instance_table",
    "pai_sensor_table", "pai_group_tag_table", "pai_machine_spec",
    "pai_machine_metric",
]

# sensor -> instance -> task 3단 조인.
# 조인 키는 (job_name, task_name, worker_name).
# 5키(+inst_id,+machine)와 결과가 동일함을 확인했으므로 3키를 쓴다.
JOINED = """
    SELECT s.gpu_wrk_util, s.cpu_usage,
           t.plan_gpu, t.plan_cpu, t.gpu_type, t.task_name, t.status,
           i.start_time, i.end_time,
           (i.end_time IS NULL) AS censored
    FROM pai_sensor_table s
    JOIN pai_instance_table i
      ON s.job_name = i.job_name
     AND s.task_name = i.task_name
     AND s.worker_name = i.worker_name
    JOIN pai_task_table t
      ON s.job_name = t.job_name
     AND s.task_name = t.task_name
    WHERE t.plan_gpu IS NOT NULL AND t.plan_gpu > 0
      AND i.start_time IS NOT NULL
"""

QUERIES: list[tuple[str, str]] = [
    ("테이블 규모", """
        SELECT 'pai_job_table' AS tbl, count(*) AS n FROM pai_job_table
        UNION ALL SELECT 'pai_task_table', count(*) FROM pai_task_table
        UNION ALL SELECT 'pai_instance_table', count(*) FROM pai_instance_table
        UNION ALL SELECT 'pai_sensor_table', count(*) FROM pai_sensor_table
        UNION ALL SELECT 'pai_group_tag_table', count(*) FROM pai_group_tag_table
        UNION ALL SELECT 'pai_machine_spec', count(*) FROM pai_machine_spec
        UNION ALL SELECT 'pai_machine_metric', count(*) FROM pai_machine_metric
    """),
    ("관측 기간", """
        SELECT min(start_time) AS min_start, max(end_time) AS max_end,
               round((max(end_time) - min(start_time)) / 86400.0, 2) AS span_days
        FROM pai_instance_table
    """),
    ("end_time 결측률", """
        SELECT 'task' AS tbl, count(*) AS n,
               sum(CASE WHEN end_time IS NULL THEN 1 ELSE 0 END) AS n_null,
               round(100.0 * sum(CASE WHEN end_time IS NULL THEN 1 ELSE 0 END) / count(*), 2) AS pct
        FROM pai_task_table
        UNION ALL SELECT 'instance', count(*),
               sum(CASE WHEN end_time IS NULL THEN 1 ELSE 0 END),
               round(100.0 * sum(CASE WHEN end_time IS NULL THEN 1 ELSE 0 END) / count(*), 2)
        FROM pai_instance_table
        UNION ALL SELECT 'job', count(*),
               sum(CASE WHEN end_time IS NULL THEN 1 ELSE 0 END),
               round(100.0 * sum(CASE WHEN end_time IS NULL THEN 1 ELSE 0 END) / count(*), 2)
        FROM pai_job_table
    """),
    ("duration 이상치", """
        SELECT count(*) AS n_complete,
               sum(CASE WHEN end_time < start_time THEN 1 ELSE 0 END) AS n_negative,
               sum(CASE WHEN end_time = start_time THEN 1 ELSE 0 END) AS n_zero_length
        FROM pai_instance_table
        WHERE end_time IS NOT NULL AND start_time IS NOT NULL
    """),
    ("plan_gpu 분포 (상위 12)", """
        SELECT plan_gpu, count(*) AS n,
               round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct
        FROM pai_task_table GROUP BY 1 ORDER BY n DESC LIMIT 12
    """),
    ("plan_gpu 결측/범위", """
        SELECT sum(CASE WHEN plan_gpu IS NULL THEN 1 ELSE 0 END) AS n_null,
               sum(CASE WHEN plan_gpu > 100 THEN 1 ELSE 0 END) AS n_multi_gpu,
               count(*) AS n_total
        FROM pai_task_table
    """),
    ("task_name 분포 (상위 12) — 워크로드 역할", """
        SELECT task_name, count(*) AS n,
               round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct
        FROM pai_task_table GROUP BY 1 ORDER BY n DESC LIMIT 12
    """),
    ("group_tag.workload 채움률", """
        SELECT count(*) AS n_total,
               round(100.0 * sum(CASE WHEN workload IS NOT NULL THEN 1 ELSE 0 END) / count(*), 2) AS workload_filled_pct,
               round(100.0 * sum(CASE WHEN gpu_type_spec IS NOT NULL THEN 1 ELSE 0 END) / count(*), 2) AS gpu_spec_filled_pct
        FROM pai_group_tag_table
    """),
    ("group_tag.workload 값", """
        SELECT workload, count(*) AS n,
               round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct_of_filled
        FROM pai_group_tag_table WHERE workload IS NOT NULL
        GROUP BY 1 ORDER BY n DESC
    """),
    ("클러스터 구성 (machine_spec)", """
        SELECT gpu_type, count(*) AS machines, sum(cap_gpu)::BIGINT AS total_gpus,
               max(cap_gpu) AS gpus_per_machine
        FROM pai_machine_spec GROUP BY 1 ORDER BY total_gpus DESC
    """),
    ("gpu_wrk_util 분포", """
        SELECT count(*) AS n,
               round(100.0 * sum(CASE WHEN gpu_wrk_util = 0 THEN 1 ELSE 0 END) / count(*), 2) AS zero_pct,
               round(avg(gpu_wrk_util), 2) AS mean,
               round(median(gpu_wrk_util), 2) AS p50,
               round(quantile_cont(gpu_wrk_util, 0.9), 2) AS p90,
               round(max(gpu_wrk_util), 2) AS max
        FROM pai_sensor_table
    """),
    ("센서 커버리지", """
        SELECT
          (SELECT count(DISTINCT job_name || '|' || task_name || '|' || worker_name)
             FROM pai_instance_table) AS instance_keys,
          (SELECT count(DISTINCT job_name || '|' || task_name || '|' || worker_name)
             FROM pai_sensor_table) AS sensor_keys,
          round(100.0 *
            (SELECT count(DISTINCT job_name || '|' || task_name || '|' || worker_name) FROM pai_sensor_table) /
            (SELECT count(DISTINCT job_name || '|' || task_name || '|' || worker_name) FROM pai_instance_table),
            2) AS coverage_pct
    """),
    ("조인 팽창 검사", """
        SELECT (SELECT count(*) FROM pai_sensor_table) AS sensor_rows,
               (SELECT count(*) FROM pai_sensor_table s JOIN pai_instance_table i
                  ON s.job_name=i.job_name AND s.task_name=i.task_name
                 AND s.worker_name=i.worker_name) AS joined_3key,
               (SELECT count(*) FROM pai_sensor_table s JOIN pai_instance_table i
                  ON s.job_name=i.job_name AND s.task_name=i.task_name
                 AND s.worker_name=i.worker_name AND s.inst_id=i.inst_id
                 AND s.machine=i.machine) AS joined_5key
    """),
    ("⭐ 낭비율 — 절단 방식 A: 미완료를 관측종료로", f"""
        WITH obs AS (SELECT max(end_time) AS e FROM pai_instance_table),
             b AS ({JOINED}),
             j AS (SELECT *, (coalesce(end_time, (SELECT e FROM obs)) - start_time) / 3600.0 AS hrs FROM b)
        SELECT count(*) AS n,
               round(sum(hrs * plan_gpu / 100.0), 0) AS allocated_gpu_hours,
               round(sum(hrs * gpu_wrk_util / 100.0), 0) AS used_gpu_hours,
               round(1 - sum(hrs * gpu_wrk_util / 100.0) / sum(hrs * plan_gpu / 100.0), 4) AS waste_ratio,
               round(100.0 * sum(CASE WHEN censored THEN 1 ELSE 0 END) / count(*), 2) AS censored_pct
        FROM j WHERE hrs >= 0
    """),
    ("⭐ 낭비율 — 절단 방식 B: 미완료 제외 (채택)", f"""
        WITH b AS ({JOINED}),
             j AS (SELECT *, (end_time - start_time) / 3600.0 AS hrs FROM b WHERE end_time IS NOT NULL)
        SELECT count(*) AS n,
               round(sum(hrs * plan_gpu / 100.0), 0) AS allocated_gpu_hours,
               round(sum(hrs * gpu_wrk_util / 100.0), 0) AS used_gpu_hours,
               round(1 - sum(hrs * gpu_wrk_util / 100.0) / sum(hrs * plan_gpu / 100.0), 4) AS waste_ratio
        FROM j WHERE hrs > 0
    """),
    ("⭐ 역할(task_name)별 낭비율", f"""
        WITH b AS ({JOINED}),
             j AS (SELECT *, (end_time - start_time) / 3600.0 AS hrs FROM b WHERE end_time IS NOT NULL)
        SELECT task_name, count(*) AS n,
               round(sum(hrs * plan_gpu / 100.0), 0) AS allocated_gpu_hours,
               round(1 - sum(hrs * gpu_wrk_util / 100.0) / nullif(sum(hrs * plan_gpu / 100.0), 0), 3) AS waste_ratio
        FROM j WHERE hrs > 0 GROUP BY 1
        HAVING sum(hrs * plan_gpu / 100.0) > 100
        ORDER BY allocated_gpu_hours DESC
    """),
    ("⭐ GPU 타입별 낭비율", f"""
        WITH b AS ({JOINED}),
             j AS (SELECT *, (end_time - start_time) / 3600.0 AS hrs FROM b WHERE end_time IS NOT NULL)
        SELECT coalesce(gpu_type, '<NULL>') AS gpu_type, count(*) AS n,
               round(sum(hrs * plan_gpu / 100.0), 0) AS allocated_gpu_hours,
               round(1 - sum(hrs * gpu_wrk_util / 100.0) / nullif(sum(hrs * plan_gpu / 100.0), 0), 3) AS waste_ratio
        FROM j WHERE hrs > 0 GROUP BY 1 ORDER BY allocated_gpu_hours DESC
    """),
    ("⭐ status별 자원 소비", f"""
        WITH b AS ({JOINED}),
             j AS (SELECT *, (end_time - start_time) / 3600.0 AS hrs FROM b WHERE end_time IS NOT NULL)
        SELECT status, count(*) AS n,
               round(sum(hrs * plan_gpu / 100.0), 0) AS allocated_gpu_hours,
               round(100.0 * sum(hrs * plan_gpu / 100.0) / sum(sum(hrs * plan_gpu / 100.0)) OVER (), 2) AS pct_of_allocated,
               round(1 - sum(hrs * gpu_wrk_util / 100.0) / nullif(sum(hrs * plan_gpu / 100.0), 0), 3) AS waste_ratio
        FROM j WHERE hrs > 0 GROUP BY 1 ORDER BY allocated_gpu_hours DESC
    """),
    ("gpu_wrk_util > plan_gpu 발생률", f"""
        WITH b AS ({JOINED})
        SELECT count(*) AS n,
               sum(CASE WHEN gpu_wrk_util > plan_gpu THEN 1 ELSE 0 END) AS n_exceed,
               round(100.0 * sum(CASE WHEN gpu_wrk_util > plan_gpu THEN 1 ELSE 0 END) / count(*), 2) AS exceed_pct
        FROM b
    """),
]


def to_markdown_table(df) -> str:
    if df.empty:
        return "_(결과 없음)_"
    cols = list(df.columns)
    head = "| " + " | ".join(cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    rows = [
        "| " + " | ".join(
            f"{v:,.0f}" if isinstance(v, float) and v.is_integer() and abs(v) >= 1000
            else (f"{v}" if v is not None else "")
            for v in rec
        ) + " |"
        for rec in df.itertuples(index=False)
    ]
    return "\n".join([head, sep, *rows])


def main() -> None:
    p = argparse.ArgumentParser(description="Bronze 프로파일링 리포트 생성")
    p.add_argument("--bronze-dir", type=Path, default=BRONZE_DEFAULT)
    p.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = p.parse_args()

    con = duckdb.connect()
    for v in VIEWS:
        con.execute(f"CREATE VIEW {v} AS SELECT * FROM read_parquet('{args.bronze_dir}/{v}.parquet')")

    parts = [
        "# 데이터 프로파일 — Alibaba cluster-trace-gpu-v2020",
        "",
        "> 이 문서는 `PYTHONPATH=src python3 -m gpu_finops.ingest.profile_raw` 로 생성된다.",
        "> 손으로 고치지 말 것 — 수치를 바꾸려면 쿼리를 바꿔야 한다.",
        "",
    ]
    for title, sql in QUERIES:
        df = con.execute(textwrap.dedent(sql)).df()
        parts += [f"## {title}", "", to_markdown_table(df), ""]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(parts), encoding="utf-8")
    print(f"작성 완료: {args.out}")


if __name__ == "__main__":
    main()
