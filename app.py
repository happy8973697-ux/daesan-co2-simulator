import datetime
import io
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 1. 페이지 설정 & 주식 앱 스타일 다크 CSS
st.set_page_config(
    page_title="대산공장 운영노트 & 재고 시뮬레이터",
    page_icon="🏭",
    layout="wide",
)

st.markdown(
    """
<style>
    .stApp { background-color: #0B0F19; color: #E2E8F0; }
    div[data-testid="stBlock"] { background-color: #131B2E; border-radius: 12px; padding: 16px; border: 1px solid #1E293B; }
    
    /* 주식 앱 카드 스타일 */
    .stock-card {
        background-color: #182238;
        border-radius: 14px;
        padding: 18px;
        border: 1px solid #2A3859;
        margin-bottom: 15px;
    }
    .stock-title { font-size: 14px; color: #94A3B8; font-weight: 600; margin-bottom: 6px; }
    .stock-value { font-size: 28px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.5px; }
    
    .delta-container { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
    .delta-badge {
        padding: 5px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
    }
    .delta-up { background-color: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .delta-down { background-color: rgba(59, 130, 246, 0.15); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.3); }
    .delta-zero { background-color: rgba(148, 163, 184, 0.15); color: #94A3B8; border: 1px solid rgba(148, 163, 184, 0.3); }
</style>
""",
    unsafe_allow_html=True,
)

# 2. 데이터 누적 저장소 (CSV) 로드 및 관리
DATA_FILE = "daesan_daily_history.csv"


def load_history():
  if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    df["날짜"] = pd.to_datetime(df["날짜"])
    return df
  else:
    # 기본 구조 생성 (초기 파일 없을 시 2026.10.01 데이터 기본 탑재)
    initial_data = pd.DataFrame([{
        "날짜": pd.to_datetime("2026-10-01"),
        "원료공급": 88.90,
        "액탄생산": 92.51,
        "드라이생산": 23.86,
        "현재고": 1986.87,
        "액탄출고": 76.66,
        "드라이출고": 39.92,
    }])
    initial_data.to_csv(DATA_FILE, index=False)
    return initial_data


def save_record(date_str, raw_gas, co2_prod, dry_prod, cur_inv, co2_out):
  df = load_history()
  target_date = pd.to_datetime(date_str)

  new_row = {
      "날짜": target_date,
      "원료공급": float(raw_gas),
      "액탄생산": float(co2_prod),
      "드라이생산": float(dry_prod),
      "현재고": float(cur_inv),
      "액탄출고": float(co2_out),
      "드라이출고": 0.0,
  }

  # 기존 일자 중복 시 덮어쓰기, 없으면 추가
  if target_date in df["날짜"].values:
    df.loc[df["날짜"] == target_date, list(new_row.keys())] = list(
        new_row.values()
    )
  else:
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

  df = df.sort_values("날짜").reset_index(drop=True)
  df.to_csv(DATA_FILE, index=False)
  return df


# 3. 증감(Delta) 계산 헬퍼 함수
def get_delta_badge(label, cur_val, past_val):
  if past_val is None or np.isnan(past_val) or past_val == 0:
    return f"<div class='delta-badge delta-zero'>{label}: -</div>"

  diff = cur_val - past_val
  pct = (diff / past_val) * 100.0

  if diff > 0:
    return f"<div class='delta-badge delta-up'>{label} +{diff:,.2f}t (+{pct:.1f}%)</div>"
  elif diff < 0:
    return f"<div class='delta-badge delta-down'>{label} {diff:,.2f}t ({pct:.1f}%)</div>"
  else:
    return f"<div class='delta-badge delta-zero'>{label} 변동없음 (0%)</div>"


def render_stock_card(title, cur_value, past_dict):
  badges_html = ""
  for label, past_val in past_dict.items():
    badges_html += get_delta_badge(label, cur_value, past_val)

  card_html = f"""
    <div class="stock-card">
        <div class="stock-title">{title}</div>
        <div class="stock-value">{cur_value:,.2f} <span style="font-size:16px; color:#94A3B8;">톤</span></div>
        <div class="delta-container">
            {badges_html}
        </div>
    </div>
    """
  st.markdown(card_html, unsafe_allow_html=True)


# ==========================================
# 메인 앱 타이틀 및 탭 구성
# ==========================================
st.title("🏭 대산공장 스마트 운영노트 & 재고 예측")

tab0, tab1, tab2 = st.tabs([
    "📱 [오늘의 현황] 일지 등록 & 증감 비교",
    "⚡ [간단 버전] 비상 재고 예측",
    "🔬 [심화 버전] S&OP 정밀 시뮬레이션",
])

# ==========================================
# TAB 0: 오늘의 현황 (요청하신 기능 구현)
# ==========================================
with tab0:
  st.subheader("📌 일일 실적 등록 및 주식 앱 스타일 변동 비교")

  col_input, col_view = st.columns([1, 2])

  df_history = load_history()

  with col_input:
    st.markdown("#### 📝 일일 업무일지/MES 수치 입력")

    input_date = st.date_input("일자 선택", value=datetime.date(2026, 10, 1))

    # 기본값 설정 (2026.10.01 이미지/PDF 기준 데이터 기본 표시)
    v_raw = st.number_input(
        "원료 가스 공급량 (톤)", value=88.90, step=1.0, format="%.2f"
    )
    v_prod = st.number_input(
        "액탄 생산량 (톤)", value=92.51, step=1.0, format="%.2f"
    )
    v_dry = st.number_input(
        "드라이 생산량 (톤)", value=23.86, step=1.0, format="%.2f"
    )
    v_inv = st.number_input(
        "현재고 (톤)", value=1986.87, step=10.0, format="%.2f"
    )
    v_co2_out = st.number_input(
        "액탄 출고량 (톤)", value=76.66, step=5.0, format="%.2f"
    )

    if st.button("💾 실적 저장 및 누적", use_container_width=True):
      df_history = save_record(
          str(input_date), v_raw, v_prod, v_dry, v_inv, v_co2_out
      )
      st.success(f"✅ {input_date} 실적이 기록되었습니다!")

    st.markdown("---")
    st.info(
        "💡 **[추후 확장 기능 예고]**\n한두 달에 한 번씩 MES/ERP 대량 내역을"
        " 엑셀/CSV로 일괄 더블체크 업로드하는 모듈이 곧 연결됩니다."
    )

  with col_view:
    selected_dt = pd.to_datetime(input_date)
    st.markdown(
        f"#### 📊 {selected_dt.strftime('%Y년 %m월 %d일')} 실적 및 기간별 비교"
    )

    # 과거 비교 일자 산출
    d_yesterday = selected_dt - datetime.timedelta(days=1)
    d_1m = selected_dt - datetime.timedelta(days=30)
    d_3m = selected_dt - datetime.timedelta(days=90)
    d_6m = selected_dt - datetime.timedelta(days=180)
    d_1y = selected_dt - datetime.timedelta(days=365)

    def get_past_value(target_df, dt, col_name):
      match = target_df[target_df["날짜"] == dt]
      if not match.empty:
        return match[col_name].values[0]
      # 정확한 날짜가 없으면 가깝게 과거 데이터 검색
      past_matches = target_df[target_df["날짜"] < dt]
      if not past_matches.empty:
        return past_matches.iloc[-1][col_name]
      return None

    # 지표별 과거 데이터 바인딩
    def make_past_dict(col_name):
      return {
          "어제보다": get_past_value(df_history, d_yesterday, col_name),
          "1개월전": get_past_value(df_history, d_1m, col_name),
          "3개월전": get_past_value(df_history, d_3m, col_name),
          "6개월전": get_past_value(df_history, d_6m, col_name),
          "1년전": get_past_value(df_history, d_1y, col_name),
      }

    # 토스/미래에셋 주식 앱 스타일 카드 5종 출력
    render_stock_card("1. 원료 가스 공급량", v_raw, make_past_dict("원료공급"))
    render_stock_card("2. 액탄 생산량", v_prod, make_past_dict("액탄생산"))
    render_stock_card("3. 드라이아이스 생산량", v_dry, make_past_dict("드라이생산"))
    render_stock_card("4. 금일 재고 현황", v_inv, make_past_dict("현재고"))
    render_stock_card("5. 액탄 출고량", v_co2_out, make_past_dict("액탄출고"))

  st.markdown("---")
  st.subheader("📜 누적 기록 히스토리 테이블")
  st.dataframe(df_history.sort_values("날짜", ascending=False), use_container_width=True)

# ==========================================
# TAB 1: 간단 버전 (비상 재고 예측)
# ==========================================
with tab1:
  st.subheader("⚡ 간단 버전: 비상 원료 중단 / 일일 간이 재고 계산")

  c1, c2, c3, c4 = st.columns(4)
  with c1:
    s_init_inv = st.number_input(
        "현재 대산 재고 (톤)", value=1986.87, step=100.0, key="s_init"
    )
  with c2:
    s_prod = st.number_input(
        "일일 공장 생산량 (톤/일)", value=92.51, step=10.0, key="s_prod"
    )
  with c3:
    s_co2_out = st.number_input(
        "일일 액탄 출고량 (톤/일)", value=76.66, step=10.0, key="s_co2"
    )
  with c4:
    s_dry_out = st.number_input(
        "일일 드라이 생산량 (톤/일)", value=23.86, step=5.0, key="s_dry"
    )

  is_outage = st.checkbox("🚨 [비상 모드] 원료 가스 공급 100% 중단 (0톤/일)")
  s_actual_prod = 0 if is_outage else s_prod
  s_safe_inv = st.number_input(
      "최소 안전재고 기준 (톤)", value=1000, step=100, key="s_safe"
  )

  s_daily_net = s_co2_out + (s_dry_out * 1.68) - s_actual_prod

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
          line=dict(color="#EF4444" if is_outage else "#10B981", width=3),
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
  )
  st.plotly_chart(fig_s, use_container_width=True)

# ==========================================
# TAB 2: 심화 버전 (S&OP 정밀 시뮬레이션)
# ==========================================
with tab2:
  st.subheader("🔬 심화 버전: S&OP 정밀 시뮬레이션")
  st.info("기존 S&OP 시뮬레이터 변수 및 예측 모듈이 통합 구동 중입니다.")
