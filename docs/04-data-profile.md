# 데이터 프로파일 — Alibaba cluster-trace-gpu-v2020

> 이 문서는 `PYTHONPATH=src python3 -m gpu_finops.ingest.profile_raw` 로 생성된다.
> 손으로 고치지 말 것 — 수치를 바꾸려면 쿼리를 바꿔야 한다.

## 테이블 규모

| tbl | n |
|---|---|
| pai_job_table | 1055501 |
| pai_task_table | 1261050 |
| pai_instance_table | 7522002 |
| pai_sensor_table | 3033232 |
| pai_group_tag_table | 1055032 |
| pai_machine_spec | 1897 |
| pai_machine_metric | 2009423 |

## 관측 기간

| min_start | max_end | span_days |
|---|---|---|
| 494,366 | 6,451,192 | 68.94 |

## end_time 결측률

| tbl | n | n_null | pct |
|---|---|---|---|
| task | 1261050 | 349,561 | 27.72 |
| instance | 7522002 | 2,267,582 | 30.15 |
| job | 1055501 | 296,420 | 28.08 |

## duration 이상치

| n_complete | n_negative | n_zero_length |
|---|---|---|
| 4758813 | 0.0 | 29,709 |

## plan_gpu 분포 (상위 12)

| plan_gpu | n | pct |
|---|---|---|
| 100.0 | 442591 | 35.1 |
| 25.0 | 272243 | 21.59 |
| nan | 223965 | 17.76 |
| 50.0 | 136701 | 10.84 |
| 10.0 | 116648 | 9.25 |
| 5.0 | 17574 | 1.39 |
| 200.0 | 16312 | 1.29 |
| 20.0 | 14371 | 1.14 |
| 800.0 | 4943 | 0.39 |
| 500.0 | 4180 | 0.33 |
| 400.0 | 3563 | 0.28 |
| 15.0 | 3262 | 0.26 |

## plan_gpu 결측/범위

| n_null | n_multi_gpu | n_total |
|---|---|---|
| 223,965 | 30,349 | 1261050 |

## task_name 분포 (상위 12) — 워크로드 역할

| task_name | n | pct |
|---|---|---|
| tensorflow | 621415 | 49.28 |
| worker | 275785 | 21.87 |
| ps | 183283 | 14.53 |
| PyTorchWorker | 110784 | 8.79 |
| xComputeWorker | 27402 | 2.17 |
| evaluator | 17210 | 1.36 |
| TensorboardTask | 10681 | 0.85 |
| ReduceTask | 4136 | 0.33 |
| DecoderWorker | 4136 | 0.33 |
| JupyterTask | 2066 | 0.16 |
| TVMTuneMain | 1158 | 0.09 |
| OpenmpiTracker | 745 | 0.06 |

## group_tag.workload 채움률

| n_total | workload_filled_pct | gpu_spec_filled_pct |
|---|---|---|
| 1055032 | 9.74 | 1.96 |

## group_tag.workload 값

| workload | n | pct_of_filled |
|---|---|---|
| bert | 54887 | 53.39 |
| ctr | 27083 | 26.35 |
| nmt | 10363 | 10.08 |
| inception | 5440 | 5.29 |
| graphlearn | 3754 | 3.65 |
| resnet | 541 | 0.53 |
| xlnet | 415 | 0.4 |
| rl | 249 | 0.24 |
| vgg | 66 | 0.06 |

## 클러스터 구성 (machine_spec)

| gpu_type | machines | total_gpus | gpus_per_machine |
|---|---|---|---|
| MISC | 280 | 2240 | 8.0 |
| P100 | 798 | 1596 | 2.0 |
| V100M32 | 135 | 1080 | 8.0 |
| T4 | 497 | 994 | 2.0 |
| V100 | 104 | 832 | 8.0 |
| CPU | 83 | 0 | 0.0 |

## gpu_wrk_util 분포

| n | zero_pct | mean | p50 | p90 | max |
|---|---|---|---|---|---|
| 3033232 | 34.55 | 10.45 | 1.47 | 31.94 | 792.0 |

## 센서 커버리지

| instance_keys | sensor_keys | coverage_pct |
|---|---|---|
| 7164358 | 3033232 | 42.34 |

## 조인 팽창 검사

| sensor_rows | joined_3key | joined_5key |
|---|---|---|
| 3033232 | 3027318 | 3027318 |

## ⭐ 낭비율 — 절단 방식 A: 미완료를 관측종료로

| n | allocated_gpu_hours | used_gpu_hours | waste_ratio | censored_pct |
|---|---|---|---|---|
| 2487128 | 148,724,117 | 7,489,327 | 0.9496 | 18.71 |

## ⭐ 낭비율 — 절단 방식 B: 미완료 제외 (채택)

| n | allocated_gpu_hours | used_gpu_hours | waste_ratio |
|---|---|---|---|
| 2016601 | 2,266,602 | 842,842 | 0.6281 |

## ⭐ 역할(task_name)별 낭비율

| task_name | n | allocated_gpu_hours | waste_ratio |
|---|---|---|---|
| worker | 1553453 | 1,408,198 | 0.678 |
| PyTorchWorker | 102195 | 546,644 | 0.417 |
| tensorflow | 325424 | 294,036 | 0.77 |
| OpenmpiWorker | 1478 | 11,851 | 0.993 |
| xComputeWorker | 18621 | 1,943 | 0.22 |
| JupyterTask | 223 | 1,489 | 0.961 |
| evaluator | 8693 | 1,272 | 0.836 |
| TVMTuneMain | 846 | 923.0 | 0.489 |
| ps | 3242 | 239.0 | 0.992 |

## ⭐ GPU 타입별 낭비율

| gpu_type | n | allocated_gpu_hours | waste_ratio |
|---|---|---|---|
| MISC | 1218773 | 1,054,708 | 0.703 |
| P100 | 291377 | 525,767 | 0.607 |
| T4 | 447280 | 263,252 | 0.67 |
| V100M32 | 20865 | 258,709 | 0.324 |
| V100 | 38306 | 164,166 | 0.628 |

## ⭐ status별 자원 소비

| status | n | allocated_gpu_hours | pct_of_allocated | waste_ratio |
|---|---|---|---|---|
| Terminated | 1956438 | 2,148,153 | 94.77 | 0.624 |
| Running | 46853 | 85,765 | 3.78 | 0.711 |
| Failed | 13310 | 32,683 | 1.44 | 0.707 |

## gpu_wrk_util > plan_gpu 발생률

| n | n_exceed | exceed_pct |
|---|---|---|
| 2487128 | 57,259 | 2.3 |
