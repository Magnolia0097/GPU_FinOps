"""GPU FinOps — GPU 조달 의사결정을 위한 데이터 파이프라인.

계층 구조 (ADR-0001):
    ingest    : 트레이스 및 가격 데이터 수집
    transform : 정제 · 차원 모델링 (L1 진단)
    forecast  : 수요 · 스팟 가격 예측 (L2 예측)
    tco       : 총소유비용 · 손익분기 산출 (L3 처방)
    common    : 공통 유틸리티
"""

__version__ = "0.1.0"
