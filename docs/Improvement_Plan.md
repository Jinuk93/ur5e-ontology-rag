# UR5e Multi-Modal RAG 시스템 - 개선 계획

> **Version**: 1.0
> **최종 수정**: 2026-01-22
> **문서 목적**: 현재 시스템 분석 및 개선 방향 제시

---

## 목차

1. [현황 분석](#1-현황-분석)
2. [즉시 개선 필요 항목](#2-즉시-개선-필요-항목)
3. [중기 개선 항목](#3-중기-개선-항목)
4. [장기 고도화 항목](#4-장기-고도화-항목)
5. [우선순위 매트릭스](#5-우선순위-매트릭스)
6. [실행 계획](#6-실행-계획)

---

# 1. 현황 분석

## 1.1 강점

| 영역 | 강점 |
|------|------|
| **기능 완성도** | 모든 계획 기능 100% 구현 |
| **테스트 커버리지** | 163개 테스트, 100% 통과 |
| **문서화** | 상세한 Phase별 문서화 완료 |
| **구조화** | 레이어별 명확한 책임 분리 |
| **추적성** | trace_id 기반 전체 파이프라인 추적 가능 |

## 1.2 개선 필요 영역

| 영역 | 현황 | 목표 | 차이 |
|------|------|------|------|
| 패턴 감지 F1 | 58.33% | >85% | **26.67%p** |
| 센서 데이터량 | 7일 (604K) | 1개월 (2.6M) | **4배** |
| Embedding Fallback | 준비됨 | 활성화 | 미적용 |
| 통합 테스트 | 부분적 | End-to-End | 검증 필요 |
| 벤치마크 평가 | 미실행 | 실행 완료 | 검증 필요 |

## 1.3 현재 아키텍처 검토

### 파이프라인 통합 현황
```
현재 상태:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ API Request │───▶│ RAGService  │───▶│  Response   │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ├── VectorRetriever ✅
                          ├── GraphRetriever ✅
                          ├── Verifier ✅
                          │
                          ├── ContextEnricher ❓ (연동 확인 필요)
                          ├── SensorVerifier ❓ (연동 확인 필요)
                          └── OntologyVerifier ❓ (연동 확인 필요)
```

**확인 필요 사항**:
- RAGService에서 ContextEnricher가 실제로 호출되는가?
- Verifier에서 SensorVerifier, OntologyVerifier가 활용되는가?

---

# 2. 즉시 개선 필요 항목

## 2.1 통합 검증 (P0 - 최우선)

### 문제
백엔드 모듈이 개별적으로 구현되었으나, 전체 파이프라인 통합 검증 미완료

### 해결 방안
```python
# 통합 테스트 시나리오
def test_full_pipeline():
    """전체 파이프라인 통합 테스트"""
    # 1. API 요청
    response = client.post("/api/v1/query", json={
        "user_query": "C10 에러 발생, 최근 충돌 감지됨",
        "options": {"include_sensor": True}
    })

    # 2. 검증 항목
    assert response.status == "VERIFIED" or "PARTIAL"
    assert response.sensor_context is not None  # ContextEnricher 동작 확인
    assert response.verification.sensor_verified  # SensorVerifier 동작 확인
    assert response.verification.ontology_matched  # OntologyVerifier 동작 확인
```

### 작업 항목
- [ ] RAGService에서 ContextEnricher 호출 확인/수정
- [ ] Verifier에서 SensorVerifier, OntologyVerifier 호출 확인/수정
- [ ] End-to-End 통합 테스트 작성 (5개 시나리오)
- [ ] 센서 관련 질문 테스트 (이중 검증 확인)

### 예상 소요: 1-2일

---

## 2.2 벤치마크 평가 실행 (P0 - 최우선)

### 문제
평가 시스템이 구현되었으나 실제 실행/결과 확인 미완료

### 해결 방안
```bash
# 평가 실행
python scripts/run_evaluation.py

# 결과 확인
cat data/evaluation/results/latest.json
```

### 평가 지표 목표
| 지표 | 목표 | 측정 여부 |
|------|------|----------|
| Recall@5 | >80% | ❓ |
| Accuracy | >80% | ❓ |
| Hallucination Rate | <5% | ❓ |
| Action Safety Leak Rate | **0%** | ❓ |

### 작업 항목
- [ ] 벤치마크 데이터셋 검토 (40개 QA 쌍)
- [ ] 평가 스크립트 실행
- [ ] 결과 분석 및 보고서 작성
- [ ] 미달 지표 원인 분석

### 예상 소요: 0.5일

---

## 2.3 패턴 감지 정확도 개선 (P1)

### 문제
현재 패턴 감지 F1 스코어: 58.33% (목표: >85%)

### 원인 분석
| 지표 | 값 | 분석 |
|------|-----|------|
| Recall | 100% | 모든 실제 패턴 감지됨 ✅ |
| Precision | 41.18% | 오탐(False Positive) 많음 ❌ |

### 해결 방안

#### 방안 1: 임계값 조정
```yaml
# configs/pattern_thresholds.yaml
collision:
  fz_threshold: 500  # 현재
  fz_threshold: 600  # 상향 조정으로 오탐 감소
  rise_time_ms: 100  # 현재
  rise_time_ms: 80   # 하향 조정으로 민감도 조정
```

#### 방안 2: 추가 검증 로직
```python
def detect_collision(self, data):
    # 기존: 단순 임계값
    # 개선: 연속성 검증 추가
    spikes = self._find_spikes(data, threshold=500)

    # 추가 검증: 충돌은 짧은 시간에 급격한 변화
    validated = []
    for spike in spikes:
        if self._verify_collision_pattern(spike):
            validated.append(spike)
    return validated
```

### 작업 항목
- [ ] 오탐 패턴 분석 (어떤 유형의 오탐이 많은가?)
- [ ] 임계값 튜닝 실험
- [ ] 검증 로직 추가 구현
- [ ] 재평가 (F1 >85% 달성 확인)

### 예상 소요: 2-3일

---

# 3. 중기 개선 항목

## 3.1 센서 데이터 확장 (P2)

### 현황
- 현재: 7일 (604,800 레코드)
- 목표: 1개월 (2,592,000 레코드)

### 해결 방안
```python
# scripts/generate_sensor_data.py 수정
days = 30  # 7 → 30
anomaly_count = {
    "collision": 60,   # 일 2회 × 30일
    "vibration": 30,   # 일 1회 × 30일
    "overload": 10,    # 3일 1회
    "drift": 4         # 주 1회
}
```

### 작업 항목
- [ ] 데이터 생성 스크립트 수정
- [ ] 1개월치 데이터 생성
- [ ] 패턴 재감지 실행
- [ ] 검증

### 예상 소요: 1일

---

## 3.2 Embedding Fallback 활성화 (P2)

### 현황
EntityLinker에 Embedding 기반 매칭이 준비되어 있으나 미활성화

### 해결 방안
```python
# src/rag/entity_linker.py
class EntityLinker:
    def link(self, entities):
        for entity in entities:
            # 1. Lexicon 매칭
            result = self._match_lexicon(entity)
            if result:
                continue

            # 2. Regex 매칭
            result = self._match_rules(entity)
            if result:
                continue

            # 3. Embedding Fallback (활성화)
            result = self._match_embedding(entity)  # 현재 미활성화
            if result:
                continue
```

### 작업 항목
- [ ] Embedding 매칭 로직 구현/활성화
- [ ] 유사도 임계값 설정 (min_confidence: 0.7)
- [ ] 테스트 케이스 추가
- [ ] 성능 영향 측정 (지연 시간)

### 예상 소요: 1-2일

---

## 3.3 Dashboard-Backend 완전 연동 (P2)

### 현황
대시보드 UI가 백엔드의 모든 기능을 활용하지 않을 수 있음

### 해결 방안
```python
# src/dashboard/pages/rag_query.py
def render_answer(result):
    # 기존: 기본 답변만 표시
    st.markdown(result.answer)

    # 개선: 센서 컨텍스트 표시
    if result.sensor_context:
        render_sensor_evidence(result.sensor_context)

    # 개선: 검증 상세 표시
    render_verification_details(result.verification)

    # 개선: 온톨로지 경로 표시
    render_ontology_path(result.graph_paths)
```

### 작업 항목
- [ ] API 응답에 센서 컨텍스트 포함 확인
- [ ] 대시보드에 센서 근거 시각화 추가
- [ ] 검증 상세 정보 표시 개선
- [ ] 온톨로지 경로 시각화 추가

### 예상 소요: 2-3일

---

## 3.4 API 문서화 (P2)

### 현황
OpenAPI/Swagger 문서 자동 생성 가능하나 상세 설명 부족

### 해결 방안
```python
# src/api/routes/query.py
@router.post(
    "/query",
    response_model=QueryResponse,
    summary="질의응답 API",
    description="""
    UR5e 기술 지원 질의응답을 수행합니다.

    ## 기능
    - 에러코드 기반 검색
    - 증상 기반 검색
    - 센서 데이터 연동 (선택)

    ## 검증 상태
    - VERIFIED: 문서+센서 이중 검증 완료
    - PARTIAL: 부분 검증
    - INSUFFICIENT: 근거 부족
    """
)
async def query(request: QueryRequest) -> QueryResponse:
    ...
```

### 작업 항목
- [ ] 모든 엔드포인트에 상세 설명 추가
- [ ] 요청/응답 예시 추가
- [ ] Swagger UI 검토
- [ ] API 문서 PDF 생성

### 예상 소요: 1일

---

# 4. 장기 고도화 항목

## 4.1 실시간 센서 연동 (P3)

### 현황
현재: 시뮬레이션 데이터 (Parquet 파일)

### 목표
```
Axia80 센서 → MQTT/Kafka → 실시간 분석 → 자동 알림
```

### 아키텍처
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ ATI Axia80  │───▶│   MQTT      │───▶│  Processor  │
│   센서      │    │   Broker    │    │  (실시간)   │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                            │
                                            ▼
                                     ┌─────────────┐
                                     │ Alert/Store │
                                     └─────────────┘
```

### 작업 항목
- [ ] MQTT 브로커 설정
- [ ] 실시간 데이터 수집기 구현
- [ ] 스트리밍 패턴 감지
- [ ] 알림 시스템 연동

---

## 4.2 피드백 학습 (P3)

### 목표
사용자 피드백 → 시스템 개선 자동화

### 구현 방향
```python
# 피드백 수집
@router.post("/feedback")
async def submit_feedback(
    trace_id: str,
    rating: int,  # 1-5
    correction: Optional[str]  # 수정된 답변
):
    # 1. 피드백 저장
    feedback_store.save(trace_id, rating, correction)

    # 2. 낮은 평가 분석
    if rating <= 2:
        analyze_failure(trace_id)

    # 3. Lexicon/Rules 업데이트 제안
    if correction:
        suggest_lexicon_update(trace_id, correction)
```

### 작업 항목
- [ ] 피드백 수집 UI 추가
- [ ] 피드백 분석 모듈
- [ ] Lexicon 자동 업데이트 제안

---

## 4.3 다국어 지원 (P3)

### 현황
현재: 한국어/영어 혼용 (동의어 사전 기반)

### 목표
- 완전한 다국어 UI
- 다국어 질문 처리

### 작업 항목
- [ ] UI 다국어 리소스 분리
- [ ] 질문 언어 자동 감지
- [ ] 다국어 답변 생성

---

## 4.4 확장성 (P4)

### 목표
- 다른 로봇 모델 지원 (UR3e, UR10e, UR16e)
- 다른 센서 타입 지원
- 멀티 테넌트 구조

### 아키텍처 변경
```
현재: UR5e + Axia80 전용
목표: 플러그인 기반 다중 모델/센서 지원

┌─────────────────────────────────────┐
│           Core RAG Engine           │
├─────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐          │
│  │  UR5e   │  │  UR10e  │  ...     │
│  │ Plugin  │  │ Plugin  │          │
│  └─────────┘  └─────────┘          │
├─────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐          │
│  │ Axia80  │  │ Other   │  ...     │
│  │ Plugin  │  │ Sensor  │          │
│  └─────────┘  └─────────┘          │
└─────────────────────────────────────┘
```

---

# 5. 우선순위 매트릭스

## 5.1 우선순위 정의

| 우선순위 | 설명 | 기준 |
|----------|------|------|
| **P0** | 즉시 필요 | 시스템 품질 검증 필수 |
| **P1** | 높음 | 목표 미달 지표 개선 |
| **P2** | 중간 | 사용성/완성도 향상 |
| **P3** | 낮음 | 고도화/확장 |
| **P4** | 선택 | 장기 로드맵 |

## 5.2 항목별 우선순위

| 항목 | 우선순위 | 영향도 | 난이도 | 소요 시간 |
|------|----------|--------|--------|----------|
| 통합 검증 | **P0** | 높음 | 중간 | 1-2일 |
| 벤치마크 평가 실행 | **P0** | 높음 | 낮음 | 0.5일 |
| 패턴 감지 정확도 개선 | **P1** | 높음 | 중간 | 2-3일 |
| 센서 데이터 확장 | P2 | 중간 | 낮음 | 1일 |
| Embedding Fallback | P2 | 중간 | 중간 | 1-2일 |
| Dashboard-Backend 연동 | P2 | 중간 | 중간 | 2-3일 |
| API 문서화 | P2 | 낮음 | 낮음 | 1일 |
| 실시간 센서 연동 | P3 | 높음 | 높음 | 2-3주 |
| 피드백 학습 | P3 | 중간 | 중간 | 1-2주 |
| 다국어 지원 | P3 | 낮음 | 중간 | 1주 |
| 확장성 (멀티 모델) | P4 | 낮음 | 높음 | 1개월+ |

---

# 6. 실행 계획

## 6.1 단기 (1주 내)

### Week 1

| 일 | 작업 | 담당 | 산출물 |
|----|------|------|--------|
| Day 1 | 통합 검증 (ContextEnricher 연동) | - | 테스트 결과 |
| Day 1 | 벤치마크 평가 실행 | - | 평가 보고서 |
| Day 2-3 | 패턴 감지 정확도 개선 | - | F1 >85% |
| Day 4 | 센서 데이터 확장 (1개월) | - | 데이터 파일 |
| Day 5 | 통합 테스트 최종 확인 | - | 테스트 통과 |

## 6.2 중기 (2-4주)

### Week 2-3

| 작업 | 산출물 |
|------|--------|
| Embedding Fallback 활성화 | 개선된 EntityLinker |
| Dashboard-Backend 완전 연동 | 완성된 대시보드 |
| API 문서화 | Swagger 문서 |

### Week 4

| 작업 | 산출물 |
|------|--------|
| 전체 시스템 리뷰 | 리뷰 보고서 |
| 운영 가이드 작성 | 운영 문서 |
| Docker 배포 환경 구성 | docker-compose.yaml |

## 6.3 장기 (1-3개월)

| 월 | 작업 |
|----|------|
| Month 1 | 실시간 센서 연동 기반 구축 |
| Month 2 | 피드백 학습 시스템 |
| Month 3 | 다국어 지원 / 확장성 검토 |

---

## 7. 체크리스트

### 즉시 실행 (P0)
- [ ] RAGService → ContextEnricher 연동 확인
- [ ] Verifier → SensorVerifier 연동 확인
- [ ] Verifier → OntologyVerifier 연동 확인
- [ ] End-to-End 통합 테스트 실행
- [ ] 벤치마크 평가 실행 및 결과 확인

### 1주 내 (P1)
- [ ] 패턴 감지 오탐 원인 분석
- [ ] 패턴 감지 임계값 튜닝
- [ ] F1 >85% 달성 확인

### 1개월 내 (P2)
- [ ] 1개월치 센서 데이터 생성
- [ ] Embedding Fallback 활성화
- [ ] Dashboard 완전 연동
- [ ] API 문서 완성
- [ ] Docker 배포 환경 구성

---

**문서 버전**: 1.0
**작성일**: 2026-01-22
**다음 리뷰**: 1주 후
