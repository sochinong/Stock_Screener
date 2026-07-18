"""
universe.py

S&P500 / 나스닥100 종목 리스트 + GICS 섹터 정보를
위키피디아에서 자동으로 가져오는 모듈.

수동으로 종목 리스트를 관리할 필요 없이,
매번 이 파일을 실행하면 "오늘 기준" 최신 명단을 받아온다.
"""

# pandas는 표(테이블) 형태의 데이터를 다루는 라이브러리야.
# 엑셀 시트를 파이썬 안에서 다룬다고 생각하면 편해.
import pandas as pd

# requests는 인터넷에 있는 웹페이지에 "이거 좀 보여주세요"라고 요청을 보내는 라이브러리야.
import requests

# yfinance는 야후 파이낸스에서 주가/기업 정보를 가져오는 라이브러리야.
# 여기서는 나스닥100 종목들의 "섹터(어떤 업종인지)" 정보를 하나씩 물어보는 데 사용해.
import yfinance as yf

# time은 "잠깐 기다렸다가 다음 걸 하기" 위한 파이썬 기본 도구야.
# 너무 빨리 연속으로 많은 요청을 보내면 야후 서버가 "그만 좀 물어봐!" 하고
# 우리를 차단할 수 있어서, 요청 사이에 짧게 쉬는 시간을 넣어줄 거야.
import time

# io는 파이썬 기본 내장 도구야. 여기서는 "인터넷에서 받은 텍스트를,
# 마치 파일에서 읽은 것처럼" pandas에게 넘겨주기 위해 사용해.
import io

# typing은 "이 변수엔 이런 값만 들어와야 해"라고 힌트를 주는 도구 상자야.
# 실제로 프로그램을 막지는 않고, 코드 작성할 때 VSCode가 경고해주는 용도.
from typing import Literal

# 위키피디아에서 S&P500 명단이 있는 페이지 주소를 미리 변수로 저장해둠.
# 이렇게 주소를 변수에 담아두면, 나중에 주소가 바뀌어도 이 한 줄만 고치면 돼.
SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# 나스닥 공식 웹사이트가 "나스닥100 구성종목" 페이지를 보여줄 때
# 내부적으로 실제 사용하는 API 주소. 위키피디아보다 훨씬 안정적임.
NASDAQ100_API_URL = "https://api.nasdaq.com/api/quote/list-type/nasdaq100"

# 위키피디아 같은 사이트는 "너 사람이 쓰는 브라우저 맞아?"를 확인하려고
# User-Agent(신분증 같은 것)가 없는 요청은 막아버려(403 Forbidden 에러).
# 그래서 "나는 일반적인 크롬 브라우저입니다"라고 소개하는 문자열을 미리 만들어둠.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _fetch_tables(url: str) -> list[pd.DataFrame]:
    """
    주어진 url에 '신분증(User-Agent)'을 붙여서 접속한 뒤,
    페이지 안에 있는 모든 표(table)를 pandas 표 리스트로 반환하는 도우미 함수.

    맨 앞에 밑줄(_)을 붙인 이유: "이 함수는 이 파일 안에서만 쓰는
    내부용 함수"라는 파이썬 관습적인 표시야. (강제로 막는 건 아니고 관례)
    """
    # requests.get()으로 페이지에 접속. headers=HEADERS를 같이 보내서
    # "저는 로봇이 아니라 브라우저예요"라고 소개함.
    response = requests.get(url, headers=HEADERS)

    # 접속이 실패했으면(403, 404 등) 여기서 바로 에러를 내서 알려줌.
    # 이렇게 하면 나중에 원인 모를 에러 대신 "접속 자체가 실패했다"는 걸 바로 알 수 있어.
    response.raise_for_status()

    # response.text는 받아온 웹페이지의 내용(글자들)이야.
    # io.StringIO(...)는 이 글자 덩어리를 "파일인 척" 포장해주는 도구.
    # pd.read_html()은 원래 파일이나 인터넷 주소를 기대하는데,
    # 우리는 이미 받아온 내용을 넘겨줄 거라서 이렇게 포장해서 넘겨줘야 해.
    return pd.read_html(io.StringIO(response.text))


def get_sp500() -> pd.DataFrame:
    """위키피디아에서 S&P500 종목 리스트 + 섹터 정보를 가져온다."""

    # _fetch_tables()가 신분증(User-Agent)을 붙여서 접속한 뒤,
    # 페이지 안의 모든 표를 리스트로 가져와줌.
    # 즉, tables는 [표1, 표2, 표3, ...] 처럼 여러 개의 표가 담긴 리스트가 돼.
    tables = _fetch_tables(SP500_WIKI_URL)

    # S&P500 위키피디아 페이지에서는 항상 "첫 번째 표"가 우리가 원하는
    # 종목 명단 표라서, tables[0] (리스트의 0번째, 즉 첫 번째 항목)을 사용.
    df = tables[0]

    # 위키피디아 원본 표의 컬럼(열) 이름은 영어로 좀 딱딱해.
    # rename()을 이용해서 우리가 앞으로 코드에서 쓰기 편한 이름으로 바꿔줌.
    # {"바꾸기 전 이름": "바꾼 후 이름"} 형태로 짝지어서 넣으면 돼.
    df = df.rename(columns={
        "Symbol": "ticker",         # 종목 코드 (예: AAPL)
        "Security": "name",         # 회사 이름 (예: Apple Inc.)
        "GICS Sector": "sector",    # 큰 분류 섹터 (예: Information Technology)
        "GICS Sub-Industry": "sub_industry",  # 더 세부적인 업종
    })

    # 위키피디아 표는 "BRK.B"처럼 점(.)을 쓰는데,
    # 우리가 나중에 쓸 yfinance 라이브러리는 "BRK-B"처럼 하이픈(-)을 써야
    # 정확한 종목을 찾을 수 있어. 그래서 점을 하이픈으로 미리 바꿔줌.
    # .str.replace(찾을 문자, 바꿀 문자, regex=False)
    #   -> regex=False는 "정규식 문법으로 해석하지 말고 그냥 문자 그대로 찾아 바꿔"라는 뜻.
    df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)

    # 이 종목들이 어느 지수(index) 소속인지 표시해두는 새 컬럼을 추가.
    # 나중에 "both"로 합쳤을 때 어디 소속인지 구분하려고 미리 붙여두는 거야.
    df["index"] = "SP500"

    # 우리가 필요한 컬럼들만 순서대로 골라서 반환.
    # (원본 표에는 CIK, Date added 같은 필요 없는 컬럼도 섞여있어서 정리하는 거야)
    return df[["ticker", "name", "sector", "sub_industry", "index"]]


def _fill_sector_with_yfinance(df: pd.DataFrame) -> pd.DataFrame:
    """
    위키피디아 표에 섹터 정보가 없는 경우, yfinance로 종목을 하나씩 물어봐서
    "sector"(섹터)와 "sub_industry"(세부 업종) 컬럼을 채워주는 함수.

    이 작업은 티커 개수만큼 인터넷 요청을 보내야 해서 시간이 좀 걸려.
    """
    sectors = []       # 각 티커의 섹터를 하나씩 담을 빈 리스트
    sub_industries = []  # 각 티커의 세부 업종을 하나씩 담을 빈 리스트

    total = len(df)  # 전체 몇 개 종목을 처리해야 하는지

    # df["ticker"]에 있는 티커들을 하나씩 순서대로 꺼내옴.
    # enumerate(..., start=1)은 "몇 번째인지 번호(i)도 같이 세어줘"라는 뜻.
    for i, ticker in enumerate(df["ticker"], start=1):
        try:
            # yf.Ticker(티커).info 는 그 회사에 대한 다양한 정보를
            # 딕셔너리(사전) 형태로 돌려줘. 그 안에 "sector", "industry" 키가 있어.
            info = yf.Ticker(ticker).info

            # .get("sector", "Unknown") 은 "sector라는 키가 있으면 그 값을 쓰고,
            # 없으면 대신 'Unknown'이라고 채워라"라는 뜻. 에러 방지용 안전장치.
            sector = info.get("sector", "Unknown")

            # yfinance는 위키피디아처럼 정확히 "GICS Sub-Industry"라는 이름은 없고,
            # 대신 비슷한 역할을 하는 "industry"라는 값을 제공해. 그걸 대신 사용.
            sub_industry = info.get("industry", "Unknown")
        except Exception:
            # 어떤 이유로든(예: 티커가 이상하거나 야후 서버 문제) 실패하면
            # 프로그램 전체가 멈추지 않도록 "Unknown"으로 채우고 계속 진행.
            sector = "Unknown"
            sub_industry = "Unknown"

        sectors.append(sector)
        sub_industries.append(sub_industry)

        # 진행 상황을 화면에 찍어줌. 예: "[23/101] AAPL -> Information Technology"
        print(f"[{i}/{total}] {ticker} -> {sector}")

        # 다음 요청 보내기 전에 아주 잠깐(0.3초) 쉬어줌.
        # 너무 빨리 연속 요청하면 야후 서버가 우리를 일시적으로 차단할 수 있어서
        # 예의 바르게 속도를 조절해주는 거야.
        time.sleep(0.3)

    # 완성된 리스트들을 표의 새 컬럼으로 붙여줌.
    df["sector"] = sectors
    df["sub_industry"] = sub_industries
    return df


def get_nasdaq100() -> pd.DataFrame:
    """나스닥 공식 웹사이트가 실제로 사용하는 API에서 나스닥100 종목 리스트를
    가져오고, 섹터 정보는 yfinance로 채운다.

    (참고: 위키피디아 나스닥100 페이지는 표 구조가 자주 바뀌어서 불안정했어.
    그래서 nasdaq.com이 자기 웹사이트에서 직접 쓰는 API를 대신 사용해.
    이게 훨씬 안정적이고, 애초에 "공식" 데이터라 더 신뢰할 수 있어.)
    """
    # API도 웹페이지처럼 "너 브라우저 맞아?"를 확인하니까 신분증을 붙여서 요청.
    # accept 헤더는 "저는 JSON 형식으로 응답받고 싶어요"라고 알려주는 역할.
    api_headers = {**HEADERS, "accept": "application/json"}

    response = requests.get(NASDAQ100_API_URL, headers=api_headers)
    response.raise_for_status()

    # 이 API는 HTML 표가 아니라 JSON(파이썬의 딕셔너리와 비슷한 구조)을 돌려줘.
    # response.json()으로 바로 파이썬이 다룰 수 있는 형태로 변환.
    payload = response.json()

    # 이 API의 JSON 구조는 data -> data -> rows 순서로 한 겹씩 파고 들어가야
    # 실제 종목 리스트(rows)가 나와. (nasdaq.com 웹사이트 내부 규칙이라 그냥 정해진 형태)
    rows = payload["data"]["data"]["rows"]

    # rows는 [{"symbol": "AAPL", "companyName": "Apple Inc.", ...}, {...}, ...]
    # 형태의 리스트야. pd.DataFrame()에 바로 넣으면 표로 변환돼.
    df = pd.DataFrame(rows)

    # API가 주는 컬럼 이름을 우리가 쓰는 이름으로 통일.
    df = df.rename(columns={"symbol": "ticker", "companyName": "name"})

    # 점(.)을 하이픈(-)으로 바꿔서 yfinance가 인식할 수 있는 형태로 맞춤.
    df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)

    # ticker, name 컬럼만 남기고 나머지(시가총액 등 지금 안 쓰는 컬럼)는 정리.
    df = df[["ticker", "name"]].copy()

    print(f"나스닥100 섹터 정보를 yfinance로 조회합니다 (총 {len(df)}개, 시간이 좀 걸려요)...")
    df = _fill_sector_with_yfinance(df)

    # 이 종목들은 나스닥100 소속이라고 표시.
    df["index"] = "NASDAQ100"

    return df[["ticker", "name", "sector", "sub_industry", "index"]]


def get_universe(source: Literal["sp500", "nasdaq100", "both"] = "both") -> pd.DataFrame:
    """
    source에 따라 원하는 종목 명단을 반환한다.

    - "sp500"     : S&P500만
    - "nasdaq100" : 나스닥100만
    - "both"      : 둘 다 합치고, 겹치는 종목(둘 다 속한 종목)은 하나로 정리
    """

    # source 값이 "sp500"이면 S&P500 함수만 실행해서 바로 결과를 돌려줌.
    if source == "sp500":
        return get_sp500()

    # source 값이 "nasdaq100"이면 나스닥100 함수만 실행.
    if source == "nasdaq100":
        return get_nasdaq100()

    # source 값이 "both"이면 두 표를 각각 가져온 뒤 하나로 합침.
    if source == "both":
        sp500 = get_sp500()
        nasdaq100 = get_nasdaq100()

        # pd.concat()은 여러 개의 표를 위아래로 이어붙이는 함수.
        # ignore_index=True는 "이어붙인 후에 줄 번호(인덱스)를 0부터 새로 매겨라"는 뜻.
        combined = pd.concat([sp500, nasdaq100], ignore_index=True)

        # 예를 들어 애플(AAPL)은 S&P500에도, 나스닥100에도 동시에 들어있어.
        # 그래서 합치면 같은 종목이 두 번 나올 수 있는데,
        # drop_duplicates()로 중복을 제거함.
        # subset="ticker" -> "ticker" 컬럼 값이 같으면 중복으로 간주.
        # keep="first" -> 중복이면 먼저 나온 것(S&P500 쪽)만 남기고 나머지는 삭제.
        combined = combined.drop_duplicates(subset="ticker", keep="first")

        # 중복 제거하면서 줄 번호가 듬성듬성해졌을 수 있으니 다시 0부터 정렬.
        return combined.reset_index(drop=True)

    # 위의 세 가지 경우("sp500", "nasdaq100", "both") 어디에도 해당 안 되면
    # 잘못된 값이 들어온 것이므로 에러를 내서 알려줌.
    raise ValueError(f"알 수 없는 source 값입니다: {source}")


# 아래 부분은 "이 파일을 직접 실행했을 때만" 동작하는 코드야.
# 다른 파일에서 이 universe.py를 불러와서(import) 함수만 쓸 때는
# 이 아래 부분은 실행되지 않아.
if __name__ == "__main__":
    # 기본값인 "both"로 S&P500 + 나스닥100을 합친 명단을 가져와봄.
    df = get_universe("both")

    # 총 몇 개의 종목을 가져왔는지 출력.
    # len(df)는 표의 "행(줄) 개수", 즉 종목 개수를 세어줌.
    print(f"총 {len(df)}개 종목을 불러왔습니다.\n")

    # 표의 맨 위 10개 줄만 미리보기로 출력.
    print(df.head(10))

    # index(SP500 / NASDAQ100)별로 종목이 몇 개씩 있는지 세어서 출력.
    print("\n[index별 종목 수]")
    print(df["index"].value_counts())

    # 섹터(GICS Sector)별로 종목이 몇 개씩 있는지 세어서 출력.
    # 예: Information Technology 65개, Health Care 60개 ... 이런 식으로 나옴.
    print("\n[섹터(GICS Sector)별 종목 수]")
    print(df["sector"].value_counts())