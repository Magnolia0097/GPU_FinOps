"""Alibaba cluster-trace-gpu-v2020 원본 스키마 정의.

원본 CSV에는 **헤더 행이 없다.** 컬럼명은 배포본에 동봉된 `*.header`
파일에 별도로 들어 있으며, 아래 정의는 그 파일들을 그대로 옮긴 것이다.

따라서 CSV를 읽을 때는 반드시 컬럼명을 명시적으로 주입해야 한다.
헤더가 있다고 가정하면 첫 데이터 행이 조용히 사라진다.
"""

from __future__ import annotations

# 원본 헤더 파일 기준 컬럼 순서 (순서가 곧 CSV 컬럼 위치이므로 바꾸지 말 것)
COLUMNS: dict[str, list[str]] = {
    "pai_job_table": [
        "job_name", "inst_id", "user", "status", "start_time", "end_time",
    ],
    "pai_task_table": [
        "job_name", "task_name", "inst_num", "status", "start_time", "end_time",
        "plan_cpu", "plan_mem", "plan_gpu", "gpu_type",
    ],
    "pai_instance_table": [
        "job_name", "task_name", "inst_name", "worker_name", "inst_id",
        "status", "start_time", "end_time", "machine",
    ],
    "pai_sensor_table": [
        "job_name", "task_name", "worker_name", "inst_id", "machine",
        "gpu_name", "cpu_usage", "gpu_wrk_util", "avg_mem", "max_mem",
        "avg_gpu_wrk_mem", "max_gpu_wrk_mem",
        "read", "write", "read_count", "write_count",
    ],
    "pai_group_tag_table": [
        "inst_id", "user", "gpu_type_spec", "group", "workload",
    ],
    "pai_machine_spec": [
        "machine", "gpu_type", "cap_cpu", "cap_mem", "cap_gpu",
    ],
    "pai_machine_metric": [
        "worker_name", "machine", "start_time", "end_time",
        "machine_cpu_iowait", "machine_cpu_kernel", "machine_cpu_usr",
        "machine_gpu", "machine_load_1", "machine_net_receive",
        "machine_num_worker", "machine_cpu",
    ],
}

# DuckDB read_csv 용 타입. 지정하지 않으면 샘플링 추론에 맡겨져
# 대용량 파일에서 타입이 뒤바뀔 수 있다.
DTYPES: dict[str, dict[str, str]] = {
    "pai_job_table": {
        "start_time": "DOUBLE", "end_time": "DOUBLE",
    },
    "pai_task_table": {
        "inst_num": "DOUBLE", "start_time": "DOUBLE", "end_time": "DOUBLE",
        "plan_cpu": "DOUBLE", "plan_mem": "DOUBLE", "plan_gpu": "DOUBLE",
    },
    "pai_instance_table": {
        "start_time": "DOUBLE", "end_time": "DOUBLE",
    },
    "pai_sensor_table": {
        "cpu_usage": "DOUBLE", "gpu_wrk_util": "DOUBLE",
        "avg_mem": "DOUBLE", "max_mem": "DOUBLE",
        "avg_gpu_wrk_mem": "DOUBLE", "max_gpu_wrk_mem": "DOUBLE",
        "read": "DOUBLE", "write": "DOUBLE",
        "read_count": "DOUBLE", "write_count": "DOUBLE",
    },
    "pai_machine_spec": {
        "cap_cpu": "DOUBLE", "cap_mem": "DOUBLE", "cap_gpu": "DOUBLE",
    },
    "pai_machine_metric": {
        "start_time": "DOUBLE", "end_time": "DOUBLE",
        "machine_cpu_iowait": "DOUBLE", "machine_cpu_kernel": "DOUBLE",
        "machine_cpu_usr": "DOUBLE", "machine_gpu": "DOUBLE",
        "machine_load_1": "DOUBLE", "machine_net_receive": "DOUBLE",
        "machine_num_worker": "DOUBLE", "machine_cpu": "DOUBLE",
    },
}

TABLES: list[str] = list(COLUMNS)

# 단위 규약 (docs/01-metric-dictionary.md 와 일치시킬 것)
#   plan_gpu      : 백분율.  50  = GPU 0.5장   -> /100 필요
#   plan_cpu      : 백분율.  600 = 6 vCPU      -> /100 필요
#   gpu_wrk_util  : 백분율.                     -> /100 필요
#   start/end_time: 트레이스 시작 기준 경과 초
PERCENT_COLUMNS = {"plan_gpu", "plan_cpu", "gpu_wrk_util", "cpu_usage"}


def read_csv_sql(table: str, path: str) -> str:
    """헤더 없는 원본 CSV를 컬럼명과 타입을 주입해 읽는 DuckDB SQL."""
    cols = COLUMNS[table]
    types = DTYPES.get(table, {})
    spec = ", ".join(
        f"'{c}': '{types.get(c, 'VARCHAR')}'" for c in cols
    )
    return (
        f"read_csv('{path}', header=false, columns={{{spec}}}, "
        f"nullstr='', ignore_errors=false)"
    )
