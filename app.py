import io
import pandas as pd
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="대산공장 액탄 재고 예측 시뮬레이터",
    page_icon="🏭",
    layout="wide",
)

st.title("🏭 대산공장 액탄 재고 선제적 예측 시뮬레이터")
st.markdown(
    "영업 및 생산 계획 데이터를 바탕으로 향후 대산공장 탱크 재고 및 안전 수위를"
    " 선제적으로 예측합니다."
)

# 사이드바 변수 설정
st.sidebar.header("⚙️ 시뮬레이션 변수 설정")
initial_inv = st.sidebar.number_input(
    "초기 탱크 재고 (톤)",
    min_value=0.0,
    max_value=10000.0,
    value=3674.4,
    step=10.0,
)
dry_ratio = st.sidebar.number_input(
    "드라이 실효 소모 원단위 (Net)",
    min_value=1.0,
    max_value=3.0,
    value=1.68,
    step=0.01,
)
apply_shift = st.sidebar.checkbox(
    "배차확정 입고 시차(+1일) 보정 적용", value=True
)

st.sidebar.subheader("🛡️ 안전재고 기준 설정")
min_safe = st.sidebar.number_input(
    "최소 안전재고 (톤)",
    min_value=0.0,
    max_value=5000.0,
    value=1000.0,
    step=50.0,
)
max_safe = st.sidebar.number_input(
    "최대 안전재고 (톤)",
    min_value=1000.0,
    max_value=10000.0,
    value=3800.0,
    step=50.0,
)

# 계획 데이터 입력 옵션
st.subheader("📥 영업 및 생산 계획 데이터 입력")
input_method = st.radio(
    "입력 방식을 선택하세요:",
    ["샘플 데이터 사용 (2025년 10월)", "엑셀/CSV 파일 직접 업로드", "웹 화면에서 직접 수정"],
    horizontal=True,
)

sample_data = {
    "날짜": [
        "2025-10-01",
        "2025-10-02",
        "2025-10-03",
        "2025-10-04",
        "2025-10-05",
        "2025-10-06",
        "2025-10-07",
        "2025-10-08",
        "2025-10-09",
        "2025-10-10",
    ],
    "예상_공장생산(톤)": [
        27.89,
        42.20,
        29.99,
        36.89,
        20.03,
        9.91,
        42.79,
        27.41,
        29.28,
        36.04,
    ],
    "배차확정_입고(톤)": [
        77.99,
        85.62,
        0.00,
        0.00,
        0.00,
        19.35,
        9.00,
        4.26,
        94.17,
        113.34,
    ],
    "액탄_출고계획(톤)": [
        117.97,
        95.13,
        106.79,
        119.34,
        118.94,
        138.24,
        120.07,
        137.50,
        135.10,
        100.36,
    ],
    "드라이_생산계획(톤)": [
        42.38,
        54.05,
        50.72,
        18.44,
        30.56,
        3.36,
        47.07,
        62.66,
        59.38,
        55.35,
    ],
}

if input_method == "샘플 데이터 사용 (2025년 10월)":
  df_input = pd.DataFrame(sample_data)
elif input_method == "엑셀/CSV 파일 직접 업로드":
  uploaded_file = st.file_uploader(
      "계획 파일 업로드 (.xlsx 또는 .csv)", type=["xlsx", "csv"]
  )
  if uploaded_file is not None:
    try:
      df_input = (
          pd.read_csv(uploaded_file)
          if uploaded_file.name.endswith(".csv")
          else pd.read_excel(uploaded_file)
      )
      st.success("파일 업로드 성공!")
    except Exception as e:
      st.error(f"파일 오류: {e}")
      df_input = pd.DataFrame(sample_data)
  else:
    df_input = pd.DataFrame(sample_data)
else:
  df_input = st.data_editor(pd.DataFrame(sample_data), num_rows="dynamic")

# 연산 및 시뮬레이션
df_input["보정_입고(톤)"] = (
    df_input["배차확정_입고(톤)"].shift(1).fillna(0.0)
    if apply_shift
    else df_input["배차확정_입고(톤)"]
)
df_input["드라이_액탄소모(톤)"] = (
    df_input["드라이_생산계획(톤)"] * dry_ratio
).round(2)

sim_inv, alerts = [], []
curr = initial_inv

for idx, row in df_input.iterrows():
  nxt = round(
      curr
      + row["예상_공장생산(톤)"]
      + row["보정_입고(톤)"]
      - row["액탄_출고계획(톤)"]
      - row["드라이_액탄소모(톤)"],
      2,
  )
  sim_inv.append(nxt)

  if nxt < min_safe:
    alerts.append("⚠️ 경고 (재고 부족)")
  elif nxt > max_safe:
    alerts.append("🚨 경고 (탱크 만조)")
  else:
    alerts.append("✅ 정상 (안전 수위)")
  curr = nxt

df_input["예상_마감재고(톤)"] = sim_inv
df_input["안전상태"] = alerts

# KPI 메트릭
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
col1.metric("최종 마감 예상재고", f"{sim_inv[-1]:,.2f} 톤")
col2.metric("기간 내 최저 재고", f"{min(sim_inv):,.2f} 톤")
col3.metric("기간 내 최고 재고", f"{max(sim_inv):,.2f} 톤")
warn_cnt = sum(1 for a in alerts if "경고" in a)
col4.metric(
    "위험 발생 일수",
    f"{warn_cnt} 일",
    delta_color="inverse" if warn_cnt > 0 else "normal",
)

# 차트 및 테이블
st.subheader("📈 일별 예상 재고 추이 및 안전 가이드라인")
chart_df = df_input[["날짜", "예상_마감재고(톤)"]].set_index("날짜")
chart_df["최소 안전선 (1,000톤)"] = min_safe
chart_df["최대 안전선 (3,800톤)"] = max_safe
st.line_chart(chart_df)

st.subheader("📋 일자별 세부 시뮬레이션 결과")
st.dataframe(
    df_input[[
        "날짜",
        "예상_공장생산(톤)",
        "보정_입고(톤)",
        "액탄_출고계획(톤)",
        "드라이_액탄소모(톤)",
        "예상_마감재고(톤)",
        "안전상태",
    ]],
    use_container_width=True,
)

# 엑셀 다운로드
output = io.BytesIO()
with pd.ExcelWriter(output, engine="openpyxl") as writer:
  df_input.to_excel(writer, index=False, sheet_name="대산_재고예측결과")

st.download_button(
    label="📥 시뮬레이션 결과 엑셀 다운로드",
    data=output.getvalue(),
    file_name="대산공장_액탄재고_예측결과.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
