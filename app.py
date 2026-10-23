import datetime
import io
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="대산공장 액탄 재고 시뮬레이터",
    page_icon="🏭",
    layout="wide",
)

st.markdown(
    """
<style>
    .stApp { background-color: #0B0F19; color: #E2E8F0; }
    div[data-testid="stBlock"] { background-color: #131B2E; border-radius: 10px; padding: 15px; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🏭 대산공장 액탄 재고 선제 예측 시뮬레이터")
st.caption(
    "현장 실무 변수(원료 수율, 드라이 대산액탄 투입비중, 거래처별 수급계획) 반영"
    " 모델"
)

# 사이드바: 현장 실무 변수 제어판
st.sidebar.header("⚙️ 현장 변수 설정 (Variables)")

init_inv = st.sidebar.number_input("현재 대산 탱크 재고 (톤)", value=3500, step=100)
min_safe = st.sidebar.number_input("최소 안전재고 기준 (톤)", value=1000, step=100)

st.sidebar.markdown("---")
st.sidebar.subheader("🏭 생산 & 수율 변수")
gas_input = st.sidebar.number_input(
    "일일 원료가스 유입량 (톤/일)", value=140, step=10
)
yield_rate = st.sidebar.slider(
    "원료가스 가동 수율 (%)", min_value=50, max_value=120, value=85, step=5
)
actual_daily_prod = gas_input * (yield_rate / 100.0)
st.sidebar.info(f"💡 예상 일일 액탄 생산량: {actual_daily_prod:.1f} 톤/일")

st.sidebar.markdown("---")
st.sidebar.subheader("🧊 드라이아이스 생산 변수")
dry_ratio = st.sidebar.number_input(
    "드라이 표준 원단위", value=1.68, step=0.01
)
daesan_dry_share = st.sidebar.slider(
    "드라이 생산 시 [대산 액탄] 사용 비중 (%)",
    min_value=0,
    max_value=100,
    value=100,
    step=10,
)
st.sidebar.caption(
    "※ 타 공장/외부 사입 액탄으로 드라이를 만들 경우 비중을 낮춰주세요."
)

st.sidebar.markdown("---")
st.sidebar.subheader("🚚 외부 수급 (사입/이송)")
shift_leadtime = st.sidebar.checkbox("배차입고 현장 시차(+1일) 보정", value=True)

# 메인 화면: 계획 데이터 및 결과
tab1, tab2 = st.tabs(
    ["📈 30일 재고 추이 시뮬레이션", "📋 세부 데이터 확인 및 엑셀 다운로드"]
)

# 기본 월초 수급계획 샘플 (일별 거래처 합산 출고 계획)
sample_plan = pd.DataFrame({
    "날짜": [
        (datetime.date.today() + datetime.timedelta(days=i)).strftime("%m/%d")
        for i in range(30)
    ],
    "거래처합산_액탄출고계획(톤)": [110 if i % 7 < 5 else 70 for i in range(30)],
    "드라이_생산계획(톤)": [40 if i % 7 < 5 else 20 for i in range(30)],
    "외부입고_확정분(톤)": [100 if i in [5, 15, 25] else 0 for i in range(30)],
})

with tab1:
  st.subheader("📊 향후 30일 재고 예측 결과")

  # 연산 계산
  df = sample_plan.copy()
  df["보정_입고(톤)"] = (
      df["외부입고_확정분(톤)"].shift(1).fillna(0.0)
      if shift_leadtime
      else df["외부입고_확정분(톤)"]
  )

  # 드라이 액탄 실효 소모량 = 드라이생산량 * 1.68 * (대산액탄비중 %)
  df["드라이_대산액탄소모(톤)"] = (
      df["드라이_생산계획(톤)"] * dry_ratio * (daesan_dry_share / 100.0)
  ).round(2)

  sim_inv = []
  curr = init_inv
  for _, r in df.iterrows():
    # 하루 재고 = 전일재고 + (원료가스유입*수율) + 보정입고 - 액탄출고 - 드라이(대산액탄소모)
    nxt = round(
        curr
        + actual_daily_prod
        + r["보정_입고(톤)"]
        - r["거래처합산_액탄출고계획(톤)"]
        - r["드라이_대산액탄소모(톤)"],
        2,
    )
    sim_inv.append(nxt)
    curr = nxt

  df["예상_마감재고(톤)"] = sim_inv

  # KPI 메트릭
  m1, m2, m3, m4 = st.columns(4)
  m1.metric("현재 재고", f"{init_inv:,.0f} 톤")
  m2.metric("30일 후 예상 재고", f"{sim_inv[-1]:,.1f} 톤")
  m3.metric("기간 내 최저 재고", f"{min(sim_inv):,.1f} 톤")
  min_day_idx = sim_inv.index(min(sim_inv))
  m4.metric(
      "최저 재고 도달일",
      f"{df['날짜'].iloc[min_day_idx]}",
      delta="위험" if min(sim_inv) < min_safe else "안전",
      delta_color="inverse",
  )

  # Chart
  fig = go.Figure()
  fig.add_trace(
      go.Scatter(
          x=df["날짜"],
          y=df["예상_마감재고(톤)"],
          mode="lines+markers",
          name="대산 탱크 예상 재고",
          line=dict(color="#10B981", width=3),
      )
  )
  fig.add_trace(
      go.Scatter(
          x=df["날짜"],
          y=[min_safe] * 30,
          mode="lines",
          name="안전재고선 (1,000톤)",
          line=dict(color="#EF4444", dash="dot"),
      )
  )
  fig.update_layout(
      template="plotly_dark",
      paper_bgcolor="#131B2E",
      plot_bgcolor="#131B2E",
      height=380,
  )
  st.plotly_chart(fig, use_container_width=True)

with tab2:
  st.subheader("📋 세부 계산 시트")
  st.dataframe(df, use_container_width=True)

  # Excel Download
  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="대산재고예측")
  st.download_button(
      "📥 시뮬레이션 결과 엑셀 다운로드",
      data=output.getvalue(),
      file_name="대산공장_30일_재고예측.xlsx",
    )
