import re
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---------------------- 파일 경로 ----------------------
mf_path = "202508_202508_연령별인구현황_월간_남녀구분.csv"
total_path = "202508_202508_연령별인구현황_월간_남녀합계.csv"

# ---------------------- CSV 불러오기 ----------------------
mf_df = pd.read_csv(mf_path, encoding='cp949')
total_df = pd.read_csv(total_path, encoding='cp949')

# ---------------------- 컬럼 정리 ----------------------
mf_df.columns = mf_df.columns.str.strip()
total_df.columns = total_df.columns.str.strip()

# ---------------------- 연령 컬럼만 추출 ----------------------
age_cols_mf = [col for col in mf_df.columns if "세" in col]
age_cols_total = [col for col in total_df.columns if "세" in col]

# ---------------------- 숫자 변환(안전) ----------------------
def clean_numeric(df, cols):
    df = df.copy()
    for col in cols:
        s = (df[col].astype(str)
                     .str.replace("\u00a0", "", regex=False)   # NBSP 제거
                     .str.replace(",", "", regex=False)
                     .str.strip())
        df[col] = pd.to_numeric(s, errors="coerce").astype("Int64")  # nullable int
    return df

mf_df = clean_numeric(mf_df, age_cols_mf)
total_df = clean_numeric(total_df, age_cols_total)

# ---------------------- 지역 정규화 ----------------------
def normalize_region_series(s: pd.Series) -> pd.Series:
    """
    - 끝의 (숫자코드) 제거: '경기도  (4100000000)' -> '경기도'
    - 다중 공백/NBSP 정리
    - '…구 구', '…시 시' 같은 중복 단위 제거
    """
    s = (s.astype(str)
           .str.replace("\u00a0", "", regex=False)                 # NBSP
           .str.replace(r"\s+", " ", regex=True)                   # 다중 공백
           .str.replace(r"\s*\([^)]+\)\s*$", "", regex=True)       # (코드) 제거
           .str.strip())
    # 끝에 같은 단위가 중복된 경우 정리: '기흥구 구' -> '기흥구'
    s = s.str.replace(r"(시|군|구)\s*\1$", r"\1", regex=True)
    return s

# 남녀구분 파일 기준 지역 옵션 (피라미드 탭)
mf_df["지역"] = normalize_region_series(mf_df["행정구역"])
region_options = sorted(mf_df["지역"].dropna().unique().tolist())

# 남녀합계 파일 기준 지역 옵션 (전체 인구 탭)
total_df["지역"] = normalize_region_series(total_df["행정구역"])
region_options_total = sorted(total_df["지역"].dropna().unique().tolist())

# ---------------------- Streamlit UI ----------------------
st.title("🧭 연령별 인구 시각화 대시보드")
tab1, tab2 = st.tabs(["👫 남녀 인구 피라미드", "👥 전체 인구 구조"])

# ---------------------- Tab 1: 남녀 인구 피라미드 ----------------------
with tab1:
    region = st.selectbox("지역 선택 (남녀 피라미드)", region_options, key="tab1")
    filtered = mf_df[mf_df['지역'] == region]  # 정규화된 명칭으로 정확 일치

    if not filtered.empty:
        male_cols = [col for col in age_cols_mf if "_남_" in col]
        female_cols = [col for col in age_cols_mf if "_여_" in col]

        # 연령 라벨은 남성 컬럼명 뒤쪽 파트 사용
        age_labels = [col.split("_")[-1] for col in male_cols]

        male = filtered.iloc[0][male_cols].fillna(0).astype(int).values * -1  # 좌측
        female = filtered.iloc[0][female_cols].fillna(0).astype(int).values

        fig = go.Figure()
        fig.add_trace(go.Bar(x=male, y=age_labels, orientation='h', name='남성', marker_color='blue'))
        fig.add_trace(go.Bar(x=female, y=age_labels, orientation='h', name='여성', marker_color='red'))
        fig.update_layout(
            title=f"{region} 인구 피라미드",
            barmode='relative',
            xaxis=dict(title='인구 수'),
            yaxis=dict(title='연령'),
            height=700
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("해당 지역 데이터가 없습니다.")

# ---------------------- Tab 2: 전체 인구 구조 (남녀합계 파일 사용) ----------------------
with tab2:
    region2 = st.selectbox("지역 선택 (전체 인구)", region_options_total, key="tab2")
    filtered2 = total_df[total_df['지역'] == region2]  # 정규화된 명칭으로 정확 일치

    if not filtered2.empty:
        # 라벨은 기존 규칙 유지(언더스코어 기준 뒤쪽)
        age_labels = [col.split("_")[-1] for col in age_cols_total]
        total_pop = filtered2.iloc[0][age_cols_total].fillna(0).astype(int).values

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=age_labels, y=total_pop, mode='lines+markers', name='총인구'))
        fig2.update_layout(
            title=f"{region2} 연령별 인구 구조 (남녀합계 기준)",
            xaxis_title='연령',
            yaxis_title='인구 수',
            height=600
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("해당 지역 데이터가 없습니다.")
