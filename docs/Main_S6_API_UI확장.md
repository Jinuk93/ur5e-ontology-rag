# Main-S6: API/UI 확장

> **Phase**: Main-S6 (센서 통합 Phase 6)
> **목표**: 센서 데이터 시각화 및 검증 상태 표시
> **선행 조건**: Main-S1~S5 완료
> **상태**: 설계

---

## 1. 개요

### 1.1 목적

센서 데이터와 검증 결과를 사용자에게 시각적으로 제공합니다.

```
[기존 UI]
질문 → 답변 + 출처

[확장 UI]
질문 → 답변 + 출처 + 센서 분석 결과 + 검증 상태
```

### 1.2 핵심 변경사항

1. **센서 분석 페이지**: 감지된 패턴, 시계열 데이터 시각화
2. **검증 상태 표시**: VERIFIED/PARTIAL_*/UNVERIFIED 시각화
3. **이중 증거 배지**: 문서 + 센서 증거 아이콘/배지
4. **패턴-에러 관계 시각화**: 온톨로지 그래프 확장

---

## 2. Streamlit 대시보드 확장

### 2.1 새 페이지: 센서 분석 (Sensor Analysis)

```python
# src/dashboard/pages/sensor_analysis.py

def render_sensor_analysis():
    st.title("📊 센서 분석")

    # 1. 감지된 패턴 요약
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("충돌 패턴", pattern_counts["collision"])
    with col2:
        st.metric("진동 패턴", pattern_counts["vibration"])
    ...

    # 2. 시계열 차트
    st.subheader("센서 시계열 데이터")
    chart = plot_sensor_timeseries(sensor_data)
    st.plotly_chart(chart)

    # 3. 패턴 이벤트 타임라인
    st.subheader("패턴 이벤트")
    timeline = plot_pattern_events(patterns)
    st.plotly_chart(timeline)

    # 4. 에러 연관 분석
    st.subheader("에러코드 연관 분석")
    graph = plot_pattern_error_relations(ontology_data)
    st.graphviz_chart(graph)
```

### 2.2 RAG Query 페이지 확장

```python
# src/dashboard/pages/rag_query.py 수정

def render_rag_query():
    # 기존 질문/답변 로직...

    # [Main-S6] 검증 정보 표시
    if verification_result:
        render_verification_badge(verification_result)

    # [Main-S6] 센서 증거 표시
    if verification_result.has_sensor_support:
        with st.expander("📊 센서 분석 결과"):
            render_sensor_evidence(verification_result)
```

### 2.3 검증 배지 컴포넌트

```python
def render_verification_badge(result: VerificationResult):
    """검증 상태 배지 렌더링"""
    status_config = {
        "verified": ("✅", "완전 검증됨", "success"),
        "partial_both": ("🔶", "이중 증거 (불완전)", "warning"),
        "partial_doc": ("📄", "문서 검증만", "warning"),
        "partial_sensor": ("📊", "센서 검증만", "warning"),
        "unverified": ("❌", "미검증", "error"),
        "insufficient": ("⚠️", "정보 부족", "error"),
    }

    icon, label, type_ = status_config.get(result.status.value, ("❓", "알 수 없음", "info"))

    st.markdown(f"""
    <div class="verification-badge badge-{type_}">
        {icon} {label} (신뢰도: {result.confidence:.0%})
    </div>
    """, unsafe_allow_html=True)
```

---

## 3. 센서 시각화 컴포넌트

### 3.1 시계열 차트

```python
def plot_sensor_timeseries(
    data: pd.DataFrame,
    axes: List[str] = ["Fz", "Tx", "Ty"],
    highlight_patterns: List[Dict] = None
) -> go.Figure:
    """센서 시계열 Plotly 차트"""
    fig = make_subplots(rows=len(axes), cols=1, shared_xaxes=True)

    for i, axis in enumerate(axes):
        fig.add_trace(
            go.Scatter(x=data["timestamp"], y=data[axis], name=axis),
            row=i+1, col=1
        )

    # 패턴 구간 하이라이트
    if highlight_patterns:
        for pattern in highlight_patterns:
            fig.add_vrect(
                x0=pattern["start"],
                x1=pattern["end"],
                fillcolor=pattern_colors[pattern["type"]],
                opacity=0.3
            )

    return fig
```

### 3.2 패턴 이벤트 타임라인

```python
def plot_pattern_events(patterns: List[Dict]) -> go.Figure:
    """패턴 이벤트 타임라인"""
    fig = go.Figure()

    for pattern in patterns:
        fig.add_trace(go.Scatter(
            x=[pattern["timestamp"]],
            y=[pattern["pattern_type"]],
            mode="markers",
            marker=dict(size=15, color=pattern_colors[pattern["pattern_type"]]),
            hovertext=f"{pattern['pattern_type']}\nConfidence: {pattern['confidence']:.0%}"
        ))

    return fig
```

### 3.3 패턴-에러 네트워크 그래프

```python
def plot_pattern_error_network(
    patterns: List[str],
    errors: List[str],
    relations: List[Dict]
) -> str:
    """Graphviz DOT 형식 그래프"""
    dot = """
    digraph G {
        rankdir=LR;
        node [shape=box];

        // Pattern nodes
        subgraph cluster_patterns {
            label="센서 패턴";
            {{patterns}}
        }

        // Error nodes
        subgraph cluster_errors {
            label="에러코드";
            {{errors}}
        }

        // Relations
        {{relations}}
    }
    """
    return dot
```

---

## 4. API 확장

### 4.1 센서 데이터 엔드포인트

```
GET /api/sensor/patterns
GET /api/sensor/patterns/{pattern_type}
GET /api/sensor/data?start={timestamp}&end={timestamp}
GET /api/sensor/statistics?window={time_window}
```

### 4.2 응답 모델

```python
class SensorPatternResponse(BaseModel):
    patterns: List[PatternInfo]
    total_count: int
    time_range: Tuple[datetime, datetime]

class PatternInfo(BaseModel):
    pattern_id: str
    pattern_type: str  # collision, vibration, overload, drift
    timestamp: datetime
    confidence: float
    related_error_codes: List[str]
```

### 4.3 검증 결과 엔드포인트

```
POST /api/query
→ 응답에 verification 필드 추가

{
  "answer": "...",
  "sources": [...],
  "verification": {
    "status": "verified",
    "confidence": 0.92,
    "doc_evidence_count": 2,
    "sensor_evidence": {
      "patterns": ["collision"],
      "ontology_match": true
    }
  }
}
```

---

## 5. 구현 태스크

```
Main-S6-1: 센서 분석 페이지
├── src/dashboard/pages/sensor_analysis.py 작성
├── 패턴 요약 카드
├── 시계열 차트 (Plotly)
├── 패턴 타임라인
└── 검증: 페이지 렌더링 확인

Main-S6-2: RAG Query 페이지 확장
├── src/dashboard/pages/rag_query.py 수정
├── 검증 배지 컴포넌트
├── 센서 증거 expander
└── 검증: 기존 기능 유지 확인

Main-S6-3: 시각화 컴포넌트
├── src/dashboard/components/sensor_charts.py 작성
├── plot_sensor_timeseries()
├── plot_pattern_events()
├── plot_pattern_error_network()
└── 검증: 차트 렌더링 확인

Main-S6-4: API 확장 (Optional)
├── apps/api/src/routes/sensor.py 작성
├── 센서 데이터 엔드포인트
├── 검증 결과 필드 추가
└── 검증: API 테스트
```

---

## 6. 완료 기준

- [ ] 센서 분석 페이지 구현
- [ ] RAG Query 검증 배지 표시
- [ ] 시계열 차트 구현
- [ ] 패턴 타임라인 구현
- [ ] 네비게이션 메뉴 추가
- [ ] 기존 페이지 호환성 유지

---

## 7. UI 목업

### 7.1 센서 분석 페이지

```
┌─────────────────────────────────────────────────────────────┐
│  📊 센서 분석                                                │
├─────────────────────────────────────────────────────────────┤
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                       │
│  │충돌  │ │진동  │ │과부하│ │드리프트│                     │
│  │  3   │ │  12  │ │  1   │ │  2   │                       │
│  └──────┘ └──────┘ └──────┘ └──────┘                       │
├─────────────────────────────────────────────────────────────┤
│  📈 센서 시계열                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Fz  [~~~~/\~~~~]                                       ││
│  │  Tx  [~~~~vvv~~~]                                       ││
│  │  Ty  [~~~~~~~~~~]                                       ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│  🕐 패턴 이벤트                                             │
│  ● collision (14:00)  ● vibration (15:30)  ● drift (16:00) │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 RAG Query 검증 배지

```
┌─────────────────────────────────────────────────────────────┐
│  💬 질문하기                                                │
├─────────────────────────────────────────────────────────────┤
│  질문: C153 에러 해결법                                     │
├─────────────────────────────────────────────────────────────┤
│  답변:                                                      │
│  C153 에러는 충돌로 인해 발생합니다. Safety Reset을 수행...│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ✅ 완전 검증됨 (신뢰도: 92%)                           ││
│  │ 📄 문서: 2건  📊 센서: collision 패턴  🔗 온톨로지 일치││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ▼ 📊 센서 분석 결과 (클릭하여 펼치기)                     │
└─────────────────────────────────────────────────────────────┘
```

---

**참조**: Main_S5_Verifier확장.md, Main_S2_패턴감지.md
