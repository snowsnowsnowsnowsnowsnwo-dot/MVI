# 실습 ② 기능 추가 : 천만 영화는 몇 월에 개봉할까? + 천만 영화를 2편 이상 만든 감독
# 실행 : streamlit run app_8_2_movie_plus.py
# robots.txt : 위키백과의 문서 페이지(/wiki/...)는 수집이 허용되어 있습니다.

import re
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

WIKI_URL = "https://ko.wikipedia.org/wiki/대한민국의_영화_흥행_기록"
# 위키백과는 User-Agent에 '누가, 무슨 목적으로' 요청하는지 밝히도록 권장합니다.
HEADERS = {"User-Agent": "class-crawler/1.0 (university class practice; educational use)"}


def fetch_html(url, timeout=10):
    """위키백과 문서 HTML을 가져온다. (html, 오류메시지)를 돌려준다."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.encoding = "utf-8"
        if resp.status_code != 200:
            return None, f"요청 실패 : HTTP {resp.status_code}"
        return resp.text, None
    except requests.exceptions.ConnectionError:
        return None, "서버에 연결할 수 없습니다. 인터넷 연결을 확인하세요."
    except requests.exceptions.Timeout:
        return None, "요청 시간이 초과되었습니다. 잠시 후 다시 시도하세요."


def find_ranking_table(html):
    """제목 줄에 '관객수'와 '감독'이 모두 있는 첫 번째 표(= 한국 작품 흥행 순위)를 찾는다."""
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table", class_="wikitable"):
        header = table.find("tr").get_text(" ", strip=True)
        if "관객수" in header and "감독" in header:
            return table
    return None


def table_to_dataframe(table):
    """표의 줄(tr)마다 칸(th · td)을 읽어 DataFrame으로 만든다."""
    for sup in table.find_all("sup"):          # [1] 같은 각주 번호 지우기
        sup.decompose()
    rows = table.find_all("tr")
    headers = [cell.get_text(strip=True) for cell in rows[0].find_all(["th", "td"])]
    data = []
    for tr in rows[1:]:
        cells = [cell.get_text(strip=True) for cell in tr.find_all(["th", "td"])]
        if len(cells) == len(headers):         # 칸 수가 맞는 줄만 사용
            data.append(cells)
    return pd.DataFrame(data, columns=headers)


def clean_movies(df):
    """수집한 글자를 분석할 수 있는 값으로 정제한다."""
    df = df.copy()
    df["제목"] = df["제목"].str.replace("《", "").str.replace("》", "")
    df["관객수"] = df["관객수"].apply(lambda t: int(re.sub(r"[^0-9]", "", t) or 0))
    if "개봉일" in df.columns:
        dates = pd.to_datetime(df["개봉일"], errors="coerce")   # '2014-07-30' → 날짜
        df["개봉연도"] = dates.dt.year.astype("Int64")
        df["개봉월"] = dates.dt.month.astype("Int64")
    keep = [c for c in ["순위", "제목", "감독", "개봉일", "개봉연도", "개봉월", "관객수"] if c in df.columns]
    return df[keep]


def show_release_month(df):
    """⑤ 개봉 월별 편수를 막대 차트로 보여 주고, 방학 시즌 비율을 계산한다."""
    st.write("천만 영화는 몇 월에 개봉했을까?")
    months = df["개봉월"].dropna().astype(int)
    by_month = months.value_counts().reindex(range(1, 13), fill_value=0).reset_index()
    by_month.columns = ["월", "편수"]
    by_month["월"] = by_month["월"].astype(str).str.zfill(2) + "월"
    st.bar_chart(by_month, x="월", y="편수")
    vacation = months.isin([7, 8, 12, 1, 2]).sum()
    st.caption(f"여름 · 겨울방학(7 · 8 · 12 · 1 · 2월) 개봉 : {vacation}편 / {len(months)}편")


def show_directors(df):
    """⑥ 천만 영화를 2편 이상 만든 감독을 표로 보여 준다."""
    st.write("천만 영화를 2편 이상 만든 감독")
    counts = df["감독"].value_counts()
    many = counts[counts >= 2].reset_index()
    many.columns = ["감독", "편수"]
    many["작품"] = many["감독"].apply(lambda d: ", ".join(df.loc[df["감독"] == d, "제목"]))
    st.dataframe(many, hide_index=True)


st.title("천만 영화 분석기")
st.caption("출처 : 위키백과 '대한민국의 영화 흥행 기록' (한국 작품 흥행 순위 표)")

url = st.text_input("문서 주소", WIKI_URL)

if st.button("흥행 순위 가져오기"):
    with st.spinner("위키백과에서 가져오는 중..."):
        html, error = fetch_html(url)
    if error:
        st.error(error)
    else:
        table = find_ranking_table(html)
        if table is None:
            st.warning("'관객수' 표를 찾지 못했습니다. F12로 문서의 표 구조가 바뀌었는지 확인하세요.")
        else:
            st.session_state["movies"] = clean_movies(table_to_dataframe(table))

if "movies" in st.session_state:
    df = st.session_state["movies"]
    top = df.sort_values("관객수", ascending=False).iloc[0]
    latest = df.sort_values("개봉일").iloc[-1]

    c1, c2, c3 = st.columns(3)
    c1.metric("천만 영화", f"{len(df)}편")
    c2.metric("역대 1위", top["제목"])
    c3.metric("1위 관객수", f"{top['관객수'] / 10000:,.0f}만 명")
    st.caption(f"가장 최근 천만 영화 : {latest['제목']} ({latest['개봉일']} 개봉)")

    st.dataframe(df, hide_index=True)

    st.write("관객수 상위 10편")
    top10 = df.sort_values("관객수", ascending=False).head(10)
    st.bar_chart(top10, x="제목", y="관객수", horizontal=True, sort="-관객수")

    st.write("개봉 연도별 천만 영화 수")
    by_year = df["개봉연도"].value_counts().sort_index().reset_index()
    by_year.columns = ["개봉연도", "편수"]
    by_year["개봉연도"] = by_year["개봉연도"].astype(str)
    st.bar_chart(by_year, x="개봉연도", y="편수")

    show_release_month(df)     # ⑤ 추가 기능
    show_directors(df)         # ⑥ 추가 기능
