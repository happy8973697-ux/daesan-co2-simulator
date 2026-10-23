import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="대산공장 액탄·DRY 출고계획 및 재고 시뮬레이터",
    page_icon="🏭",
    layout="wide",
)

# 2. 다크 모드 커스텀 CSS 스타일링
st.markdown(
    """
<style>
    /* 전체 배경 다크 모드 */
    .stApp {
        background-color: #0B0F19;
        color: #E2E8F0;
    }
    
    /* 사이드바 및 카드 박스 디자인 */
    div[data-testid="stBlock"] {
        background-color: #131B2E;
        border-radius: 12px;
        padding: 18px;
        border: 1px solid #1E293B;
    }
    
    /* 헤더 및 텍스트 스타일 */
    h1, h2, h3, h4 {
        color: #F8FAFC !important;
        font-family: 'Pretendard', sans-serif;
    }
    
    /* 상태 카드 커스텀 */
    .status-card-green {
        background-color: #064E3B;
        border: 1px solid #10B981;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    .status-card-yellow {
        background-color: #78350F;
        border: 1px solid #F59E0B;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    .status-card-red {
        background-color: #7F1D1D;
        border: 1px solid #EF4444;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
</style>
""",
    unsafe_allow_html=True,
)

# 3. 상단 타이틀 바
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
  st.title("🏭 대산공장 액탄·DRY 출고계획 및 재고 시뮬레이터")
  st.caption("S&OP Inventory Simulation & Decision Matrix System")

with header_col2:
  st.write("")
  st.markdown(
      "<div style='text-align: right;'><span style='color: #10B981;'>🟢 실시간"
      " 계산 연동 중</span> | 🖨️ 리포트 인쇄</div>",
      unsafe_allow_html=True,
  )

st.markdown("---")

# 4. 레이아웃 분할 (좌측 파라미터 / 우측 시뮬레이션)
left_col, right_col = st.columns([1.2, 2.8])

# ==========================================
# [LEFT PANEL] 시나리오 파라미터 설정
# ==========================================
with left_col:
  st.subheader("⚙️ 시나리오 파라미터 설정")

  # 1. 기초 재고 & 안전재고
  st.markdown("**1. 기초 재고 & 안전재고 기준**")
  p_col1, p_col2 = st.columns(2)
  with p_col1:
    init_inv = st.number_input("현재 재고 (Ton)", value=3500, step=100)
  with p_col2:
    target_safe_inv = st.number_input("안전 재고 (Ton)", value=1000, step=100)

  # 2. 일일 생산량 슬라이더
  st.markdown("**2. 평소 일일 액탄 자체 생산량**")
  daily_prod = st.slider("생산량 (Ton/일)", 0, 300, 120)

  # 3. 원료 가스 공급 감소 시나리오 비율
  st.markdown("**3. 원료 가스 공급 감소 시나리오 비율**")
  s_col1, s_col2, s_col3 = st.columns(3)
  with s_col1:
    st.caption("평소 수준")
    st.write("100% 가동")
  with s_col2:
    st.caption("공급 감소")
    st.write("50%")
  with s_col3:
    st.caption("공급 중단")
    st.write("0% (Shutdown)")

  # 4. DRY 제조 및 회수 수율 파라미터
  st.markdown("**4. DRY 제조 및 회수 수율 파라미터**")
  y_col1, y_col2 = st.columns(2)
  with y_col1:
    cost_conv = st.number_input(
        "원가 전환율 (t/t)", value=1.85, step=0.01, format="%.2f"
    )
  with y_col2:
    comp_recovery = st.number_input("컴프레서 회수율 (%)", value=30, step=5)

  # 5. 외부 반입 / 여수 이송 추가 계획
  st.markdown("**5. 외부 반입 / 여수 이송 추가 계획**")
  st.markdown("• D+6일 여수 이송: **+200 Ton**")
  st.markdown("• D+13일 외부 사입: **+150 Ton**")

# ==========================================
# [RIGHT PANEL] 향후 30일 재고 추이 시뮬레이션
# ==========================================
with right_col:
  st.subheader("📈 향후 30일 재고 추이 시뮬레이션 (30-Day Trajectory)")
  st.caption("원료 공급 시나리오별 대산공장 액탄 잔여 재고 예측 곡선")

  # 30일 데이터 시뮬레이션 연산
  days = 30
  start_date = datetime.date.today()
  date_list = [start_date + datetime.timedelta(days=i) for i in range(days)]
  date_strs = [d.strftime("%m/%d") for d in date_list]

  # 기본 일일 출고 소요량 가정 (액탄 80톤 + 드라이 30톤 x 1.68배)
  net_dry_ratio = cost_conv * (1 - comp_recovery / 100.0)
  daily_outflow = 80 + (30 * net_dry_ratio)

  # 시나리오 1: 평소 수준 (100%)
  inv_normal = [init_inv]
  # 시나리오 2: 공급 감소 (50%)
  inv_reduced = [init_inv]
  # 시나리오 3: 공급 중단 (0%)
  inv_outage = [init_inv]

  for t in range(1, days):
    # D+6, D+13 외부 반입 물량
    add_in = 200 if t == 6 else (150 if t == 13 else 0)

    # 평소
    inv_normal.append(
        inv_normal[-1] + (daily_prod * 1.0) + add_in - daily_outflow
    )
    # 감소
    inv_reduced.append(
        inv_reduced[-1] + (daily_prod * 0.5) + add_in - daily_outflow
    )
    # 중단
    inv_outage.append(
        inv_outage[-1] + (daily_prod * 0.0) + add_in - daily_outflow
    )

  # Plotly 시각화 차트 생성
  fig = go.Figure()

  # 평소 수준 (네온 그린)
  fig.add_trace(
      go.Scatter(
          x=date_strs,
          y=inv_normal,
          mode="lines+markers",
          name="평소 수준 (Normal - 100%)",
          line=dict(color="#10B981", width=3),
      )
  )

  # 공급 감소 (주황/노랑)
  fig.add_trace(
      go.Scatter(
          x=date_strs,
          y=inv_reduced,
          mode="lines+markers",
          name="공급 감소 (Reduced Scenario)",
          line=dict(color="#F59E0B", width=3),
      )
  )

  # 공급 중단 (핑크/레드 점선)
  fig.add_trace(
      go.Scatter(
          x=date_strs,
          y=inv_outage,
          mode="lines+markers",
          name="공급 중단 (Outage - 0%)",
          line=dict(color="#EF4444", width=2, dash="dash"),
      )
  )

  # 안전재고 목표선 (빨간 점선)
  fig.add_trace(
      go.Scatter(
          x=date_strs,
          y=[target_safe_inv] * days,
          mode="lines",
          name="안전재고 목표선",
          line=dict(color="#991B1B", width=2, dash="dot"),
      )
  )

  fig.update_layout(
      template="plotly_dark",
      paper_bgcolor="#131B2E",
      plot_bgcolor="#131B2E",
      height=380,
      margin=dict(l=20, r=20, t=30, b=20),
      legend=dict(
          orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
      ),
      yaxis=dict(title="액탄 재고량 (Ton)", gridcolor="#1E293B"),
      xaxis=dict(gridcolor="#1E293B"),
  )

  st.plotly_chart(fig, use_container_width=True)

  # 3개 시나리오 요약 카드
  sc_col1, sc_col2, sc_col3 = st.columns(3)
  with sc_col1:
    st.markdown(
        "<div class='status-card-green'><b>평소 수준 (Normal)</b><br>안전재고"
        " 유지</div>",
        unsafe_allow_html=True,
    )
  with sc_col2:
    st.markdown(
        "<div class='status-card-yellow'><b>공급 감소 (Reduced)</b><br>안전재고"
        " 유지</div>",
        unsafe_allow_html=True,
    )
  with sc_col3:
    st.markdown(
        "<div class='status-card-red'><b>공급 중단 (Outage)</b><br>D+29일"
        " 품절 발생</div>",
        unsafe_allow_html=True,
    )

  st.markdown("---")

  # 실무 가이드 및 권장 의사결정 Box
  st.subheader("⚠️ 실무 가이드 및 권장 의사결정 (S&OP Operational Action Plan)")
  act_col1, act_col2 = st.columns([1, 2])

  with act_col1:
    st.markdown("#### 🟢 재고 안정 상태")
    st.info("LEVEL: NORMAL\n\n현재 설정된 출고 및 공급 계획에서는 안전재고 목표가 충족됩니다.")

  with act_col2:
    st.markdown("#### 📋 공장 & 영업 권장 실행 대책")
    st.success(
        "• 현재 공급 수준에서 안정적 운영이 가능합니다.\n• DRY"
        " 컴프레서 회수율(30%)을 지속 유지하십시오."
    )
