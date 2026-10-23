import datetime
import io
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 1. 페이지 기본 설정 및 디자인
st.set_page_config(
    page_title="대산공장 액탄·DRY 재고 시뮬레이터 (S&OP)",
    page_icon="🏭",
    layout="wide",
)

st.markdown(
    """
<style>
    .stApp { background-color: #0B0F19; color: #E2E8F0; }
    div[data-testid="stBlock"] { background-color: #131B2E; border-radius: 10px; padding: 15px; border: 1px solid #1E293B; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #1E293B; border-radius: 8px; color: #94A3B8; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #2563EB !important; color: white !important; font-weight: bold; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🏭 대산공장 액탄 재고 예측 시뮬레이터")
st.caption(
    "S&OP (Sales & Operations Planning) 통합 재고 관리 및 비상 대응 시스템"
)

# 탭 구성: 간단버전 vs 심화버전
tab1, tab2 = st.tabs([
    "⚡ [간단 버전] 비상 대응 & 일일 간이 예측",
    "🔬 [심화 버전] S&OP 상세 정밀 시뮬레이션",
])

# ==========================================
# TAB 1: 간단 버전 (5초 간이 예측)
# ==========================================
with tab1:
  st.subheader("⚡ 간단 버전: 비상 원료 중단 / 일일 간이 재고 계산")
  st.markdown(
      "복잡한 조건 없이 **현재 재고**와 **일일 평균 출고/생산량**만으로 버틸 수 있는"
      " 일수를 빠르게 계산합니다."
  )

  c1, c2, c3, c4 = st.columns(4)
  with c1:
    s_init_inv = st.number_input(
        "현재 대산 재고 (톤)", value=3500, step=100, key="s_init"
    )
  with c2:
    s_prod = st.number_input(
        "일일 공장 생산량 (톤/일)", value=120, step=10, key="s_prod"
    )
  with c3:
    s_co2_out = st.number_input(
        "일일 액탄 출고량 (톤/일)", value=100, step=10, key="s_co2"
    )
  with c4:
    s_dry_out = st.number_input(
        "일일 드라이 생산량 (톤/일)", value=30, step=5, key="s_dry"
    )

  # 비상 모드 스위치
  st.markdown("---")
  e_col1, e_col2 = st.columns([1, 2])
  with e_col1:
    is_outage = st.checkbox("🚨 [비상 모드] 원료 가스 공급 100% 중단 (0톤/일)")
    s_actual_prod = 0 if is_outage else s_prod
  with e_col2:
    s_safe_inv = st.number_input(
        "최소 안전재고 기준 (톤)", value=1000, step=100, key="s_safe"
    )

  # 연산
  s_daily_net = s_co2_out + (s_dry_out * 1.68) - s_actual_prod
  if s_daily_net > 0:
    s_days_safe = int((s_init_inv - s_safe_inv) / s_daily_net)
    s_days_zero = int(s_init_inv / s_daily_net)
  else:
    s_days_safe, s_days_zero = 999, 999

  # 지표 출력
  st.markdown("---")
  m1, m2, m3, m4 = st.columns(4)
  m1.metric("일일 순 재고 감소량", f"{max(0, s_daily_net):,.1f} 톤/일")
  m2.metric(
      "안전재고(1,000톤) 도달",
      f"D+{s_days_safe} 일 후" if s_days_safe < 900 else "안전 (재고 증가)",
      delta="경고" if s_days_safe < 7 else "정상",
      delta_color="inverse",
  )
  m3.metric(
      "완전 품절(0톤) 도달",
      f"D+{s_days_zero} 일 후" if s_days_zero < 900 else "안전",
      delta_color="inverse",
  )
  m4.metric(
      "현재 공장 상태",
      "🚨 원료 중단" if is_outage else "🟢 정상 가동",
  )

  # 간이 그래프
  sim_days = 30
  dates = [
      (datetime.date.today() + datetime.timedelta(days=i)).strftime("%m/%d")
      for i in range(sim_days)
  ]
  simple_inv_list = []
  curr = s_init_inv
  for _ in range(sim_days):
    curr = max(0, curr - s_daily_net)
    simple_inv_list.append(curr)

  fig_s = go.Figure()
  fig_s.add_trace(
      go.Scatter(
          x=dates,
          y=simple_inv_list,
          mode="lines+markers",
          name="예상 재고",
          line=dict(
              color="#EF4444" if is_outage else "#10B981",
              width=3,
          ),
      )
  )
  fig_s.add_trace(
      go.Scatter(
          x=dates,
          y=[s_safe_inv] * sim_days,
          mode="lines",
          name="안전재고선",
          line=dict(color="#F59E0B", dash="dash"),
      )
  )
  fig_s.update_layout(
      template="plotly_dark",
      paper_bgcolor="#131B2E",
      plot_bgcolor="#131B2E",
      height=300,
      margin=dict(l=10, r=10, t=20, b=10),
  )
  st.plotly_chart(fig_s, use_container_width=True)

# ==========================================
# TAB 2: 심화 버전 (S&OP 상세 정밀 모드)
# ==========================================
with tab2:
  st.subheader("🔬 심화 버전: 현장 변수 통합 정밀 시뮬레이션")

  # 3컬럼 파라미터 레이아웃
  p_col1, p_col2, p_col3 = st.columns(3)

  with p_col1:
    st.markdown("#### 1. 공장 & 생산 변수")
    a_init_inv = st.number_input(
        "기초 탱크 재고 (톤)", value=3500.0, step=50.0, key="a_init"
    )
    gas_feed = st.number_input(
        "원료 가스 유입량 (톤/일)", value=140.0, step=10.0
    )
    process_yield = st.slider("원료 가스 수율 (%)", 50, 120, 85, step=5)
    calc_prod = gas_feed * (process_yield / 100.0)
    st.caption(f"➔ 예상 일일 액탄 생산량: **{calc_prod:.1f} 톤/일**")

    st.markdown("---")
    comp_status = st.checkbox(
        "DRY 회수 컴프레서 정상 가동",
        value=True,
        help="미체크 시 원단위가 1.68에서 2.35로 상승합니다.",
    )
    dry_base_ratio = 1.68 if comp_status else 2.35
    st.caption(f"➔ 적용 드라이 원단위: **{dry_base_ratio:.2f}**")

  with p_col2:
    st.markdown("#### 2. 드라이 & 영업 변수")
    daesan_dry_ratio = st.slider(
        "드라이 생산 시 [대산 액탄] 사용 비중 (%)",
        0,
        100,
        100,
        step=10,
        help="외부/타공장 액탄 혼용 시 비율을 낮춰주세요.",
    )

    st.markdown("---")
    weekend_reduction = st.checkbox("주말(토/일) 출고량 50% 감소 반영", value=True)
    leadtime_shift = st.checkbox("배차입고 현장 하차 시차(+1일) 보정", value=True)

    st.markdown("---")
    shutdown_start = st.number_input(
        "공장 정기보수 시작일 (D+N일 후, 0=없음)",
        value=0,
        min_value=0,
        max_value=30,
    )
    shutdown_dur = st.number_input(
        "정기보수 기간 (일수)", value=0, min_value=0, max_value=15
    )

  with p_col3:
    st.markdown("#### 3. 외부 수급 & 이송 계획")
    st.caption("특정 날짜에 들어오는 외부 입고 물량을 설정하세요.")
    add_in_d1 = st.number_input("D+5일 입고량 (톤)", value=150, step=50)
    add_in_d2 = st.number_input("D+12일 입고량 (톤)", value=200, step=50)

    st.markdown("---")
    a_safe_min = st.number_input(
        "최소 안전재고 (톤)", value=1000, step=100, key="a_safe"
    )
    a_safe_max = st.number_input(
        "최대 탱크 용량 (톤)", value=3800, step=100, key="a_max"
    )

  # 30일 일별 정밀 데이터 생성
  st.markdown("---")
  st.markdown("### 📅 30일 시뮬레이션 세부 계산")

  sim_days = 30
  start_dt = datetime.date.today()

  dates_list = []
  prods_list = []
  co2_outs_list = []
  dry_outs_list = []
  receipts_list = []

  for i in range(sim_days):
    cur_date = start_dt + datetime.timedelta(days=i)
    dates_list.append(cur_date.strftime("%Y-%m-%d (%a)"))

    # 1. 생산량 (정기보수 적용)
    if shutdown_start > 0 and (
        shutdown_start <= (i + 1) < (shutdown_start + shutdown_dur)
    ):
      prods_list.append(0.0)
    else:
      prods_list.append(calc_prod)

    # 2. 출고량 (주말 할인 반영)
    is_weekend = cur_date.weekday() in [5, 6]  # 5=토, 6=일
    co2_base = 110.0
    dry_base = 35.0

    if is_weekend and weekend_reduction:
      co2_outs_list.append(co2_base * 0.5)
      dry_outs_list.append(dry_base * 0.5)
    else:
      co2_outs_list.append(co2_base)
      dry_outs_list.append(dry_base)

    # 3. 외부 입고
    if (i + 1) == 5:
      receipts_list.append(float(add_in_d1))
    elif (i + 1) == 12:
      receipts_list.append(float(add_in_d2))
    else:
      receipts_list.append(0.0)

  df_adv = pd.DataFrame({
      "날짜": dates_list,
      "공장생산(톤)": prods_list,
      "외부입고_원안(톤)": receipts_list,
      "액탄출고(톤)": co2_outs_list,
      "드라이생산(톤)": dry_outs_list,
  })

  # 시차 보정
  if leadtime_shift:
    df_adv["보정_입고(톤)"] = (
        df_adv["외부입고_원안(톤)"].shift(1).fillna(0.0)
    )
  else:
    df_adv["보정_입고(톤)"] = df_adv["외부입고_원안(톤)"]

  # 드라이 액탄 실효 소모량
  df_adv["드라이_액탄소모(톤)"] = (
      df_adv["드라이생산(톤)"]
      * dry_base_ratio
      * (daesan_dry_ratio / 100.0)
  ).round(2)

  # 누적 재고 연산
  adv_sim_inv = []
  status_alerts = []
  curr_a = a_init_inv

  for _, row in df_adv.iterrows():
    next_a = (
        curr_a
        + row["공장생산(톤)"]
        + row["보정_입고(톤)"]
        - row["액탄출고(톤)"]
        - row["드라이_액탄소모(톤)"]
    )
    next_a = round(next_a, 2)
    adv_sim_inv.append(next_a)

    if next_a < a_safe_min:
      status_alerts.append("⚠️ 재고부족 경고")
    elif next_a > a_safe_max:
      status_alerts.append("🚨 탱크만조 경고")
    else:
      status_alerts.append("✅ 정상")
    curr_a = next_a

  df_adv["예상_마감재고(톤)"] = adv_sim_inv
  df_adv["상태"] = status_alerts

  # 메인 차트
  fig_a = go.Figure()
  fig_a.add_trace(
      go.Scatter(
          x=df_adv["날짜"],
          y=df_adv["예상_마감재고(톤)"],
          mode="lines+markers",
          name="대산 탱크 예측 재고",
          line=dict(color="#10B981", width=3),
      )
  )
  fig_a.add_trace(
      go.Scatter(
          x=df_adv["날짜"],
          y=[a_safe_min] * sim_days,
          mode="lines",
          name="최소 안전선 (1,000톤)",
          line=dict(color="#EF4444", dash="dot"),
      )
  )
  fig_a.add_trace(
      go.Scatter(
          x=df_adv["날짜"],
          y=[a_safe_max] * sim_days,
          mode="lines",
          name="최대 안전선 (3,800톤)",
          line=dict(color="#3B82F6", dash="dot"),
      )
  )

  fig_a.update_layout(
      template="plotly_dark",
      paper_bgcolor="#131B2E",
      plot_bgcolor="#131B2E",
      height=380,
      margin=dict(l=10, r=10, t=20, b=10),
  )
  st.plotly_chart(fig_a, use_container_width=True)

  # 세부 표 및 다운로드
  st.dataframe(df_adv, use_container_width=True)

  excel_buffer = io.BytesIO()
  with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    df_adv.to_excel(writer, index=False, sheet_name="S&OP_재고예측")

  st.download_button(
      "📥 S&OP 정밀 시뮬레이션 결과 엑셀 다운로드",
      data=excel_buffer.getvalue(),
      file_name="대산공장_S&OP_상세재고예측.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  )
