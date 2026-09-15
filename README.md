# GPU FinOps

> 실사용 GPU 트레이스로부터 수요를 집계·예측하고,
> **온디맨드 / 스팟 / 예약 / 소유(온프레미스)** 의 손익분기를 계산해 제시하는 데이터 파이프라인.

---

## 이 프로젝트가 답하려는 질문

> **"GPU, 빌리는 게 싼가 사는 게 싼가?"**

디지털데일리 「[클라우드 시대 역설…24시간 GPU 돌리자니 다시 '소유'가 답?](https://www.ddaily.co.kr/page/view/2026071100011015760)」
(2026-07-11) 는 이 선택이 **사용 패턴**에 의해 갈린다고 말한다.
24시간 상시 가동 그룹에서는 온프레미스 선호가 GPUaaS 선호의 약 4배였고,
풀 가동 기준 1년 반이면 구매 비용을 넘어선다는 것이다.

문제는 **대부분의 조직이 자기 사용 패턴을 모른다는 점**이다.
할당량(request)은 알아도 실사용량(usage)은 측정하지 않는다.

이 프로젝트는 그 갭을 데이터로 메운다.

## 핵심 산출물

프로젝트가 최종적으로 뱉는 숫자는 하나다.

```
손익분기 가동률  U* = 연간 온프레미스 TCO / (온디맨드 시간단가 × 8,760 × GPU 수)
```

→ **실측 가동률이 `U*`를 넘으면 소유, 아니면 임대.**

## Week 1 실측 결과

파이프라인을 만들기 전에 데이터부터 확인했다. 결과가 예상보다 강했다.

| 지표 | 값 |
|---|---|
| 할당 GPU-시간 | 2,266,602 |
| 실사용 GPU-시간 | 842,842 |
| **낭비율** | **62.8%** |

*완료 인스턴스 기준 · 센서 커버리지 42.3% · 미완료 30.2% 제외(과소 추정 방향)*

역할별로 보면 낭비가 어디에 몰려 있는지 드러난다.

| 역할 | 할당 GPU-시간 | 낭비율 |
|---|---|---|
| `ps` (파라미터 서버) | 239 | **99.2%** |
| `JupyterTask` (노트북) | 1,489 | **96.1%** |
| `tensorflow` | 294,036 | 77.0% |
| `worker` | 1,408,198 | 67.8% |
| `PyTorchWorker` | 546,644 | 41.7% |

→ **"파라미터 서버에 GPU를 할당하지 마라", "유휴 노트북을 자동 종료하라"**
평균 낭비율 하나보다 이런 역할 단위 권고가 실행 가능하다.

전체 프로파일: [`docs/04-data-profile.md`](docs/04-data-profile.md)

## 3계층 구조

| 계층 | 질문 | 산출물 |
|---|---|---|
| **L1 진단** | 지금 얼마를 어디에 쓰고, 얼마를 버리고 있나 | 팀/잡별 showback, 낭비 비용 정량화 |
| **L2 예측** | 앞으로 얼마나 쓸 것인가 | GPU-hour · 토큰 수요 P50/P90 |
| **L3 처방** | 그래서 빌릴까 살까 | 손익분기 곡선, 조달 믹스, 민감도 분석 |

L1은 그 자체로 독립 제품이다. L2/L3가 실패해도 프로젝트는 완결된다.

## 데이터

| 소스 | 역할 | 상태 |
|---|---|---|
| [Alibaba `cluster-trace-gpu-v2020`](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2020) | 학습/배치 워크로드 | ✅ 수집 완료 (7개 테이블, 체크섬 검증) |
| AWS Price List API / Spot Price History | 가격 (실측) | ⬜ 예정. 가격은 **하드코딩하지 않는다** (ADR-0004) |
| `config/tco.yaml` | 온프레미스 TCO 가정 | ⬜ API로 얻을 수 없는 값만, 전부 민감도 분석 대상 |
| ~~Azure LLM Inference~~ | ~~추론 서빙~~ | ❌ **개발 환경 egress 정책 차단** (ADR-0006) |

### 알려진 한계 — 숨기지 않는다

- **추론 서빙 워크로드가 없다.** Azure 트레이스 접근이 막혀 학습/배치만 다룬다.
  따라서 원 기사의 "24시간 상시 가동" 논점에 직접 답하지 못하고,
  **간헐적 학습 워크로드에서의 소유 vs 임대**라는 축소된 질문에 답한다.
- 트레이스는 2020년 V100/T4 세대이며 **가격 정보가 없다.**
- 센서 커버리지 42.3%, 미완료 인스턴스 30.2% 제외.

자세한 내용은 [`docs/02-data-sources.md`](docs/02-data-sources.md),
[`docs/failures.md`](docs/failures.md) 참조.

## 문서

| 문서 | 내용 |
|---|---|
| [`docs/00-project-charter.md`](docs/00-project-charter.md) | 문제 정의, 범위, 성공 기준 |
| [`docs/04-data-profile.md`](docs/04-data-profile.md) | **실측 프로파일 (자동 생성)** |
| [`docs/failures.md`](docs/failures.md) | **시행착오 기록** — 무엇이 틀렸고 어떻게 알아챘나 |
| [`docs/01-metric-dictionary.md`](docs/01-metric-dictionary.md) | 모든 지표의 정의·공식·그레인 |
| [`docs/02-data-sources.md`](docs/02-data-sources.md) | 데이터 소스, 스키마, 라이선스, 한계 |
| [`docs/03-roadmap.md`](docs/03-roadmap.md) | 8주 로드맵과 주차별 완료 기준 |
| [`docs/adr/`](docs/adr/) | 아키텍처 결정 기록 (왜 그렇게 했는가) |

## 현재 상태

**Week 1 완료 — 설계 및 데이터 검증**

- [x] 문제 정의 · 프로젝트 헌장
- [x] 지표 사전 v2 (실측 검증 완료)
- [x] 데이터 수집 (`scripts/fetch_data.sh`, 체크섬 7/7 통과)
- [x] Bronze 변환 (CSV 3.7GB → Parquet 1.15GB, 25초)
- [x] 스키마 실측 검증 · 프로파일링
- [x] ADR 0000–0007 (0006·0007은 실측 결과로 인한 설계 변경)
- [ ] 배치 파이프라인 (Week 2–3)

### 재현

```bash
bash scripts/fetch_data.sh                              # 수집 + 체크섬 검증
PYTHONPATH=src python3 -m gpu_finops.ingest.to_bronze   # CSV → Parquet
PYTHONPATH=src python3 -m gpu_finops.ingest.profile_raw # 프로파일 리포트 생성
```

## AI 도구 사용에 관하여

이 저장소는 AI 페어프로그래밍을 사용해 작성되었다.
아키텍처 결정, 데이터 모델 설계, 가정 설정과 검증은 직접 수행했으며
그 근거는 전부 [`docs/adr/`](docs/adr/) 에 남긴다.

**머신러닝은 베이스라인을 이겼을 때만 채택한다.** 근거는 [ADR-0005](docs/adr/0005-ml-only-when-it-beats-baseline.md).
