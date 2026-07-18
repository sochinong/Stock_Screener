"""
price_collector.py

역할
--------------------------------------------------
1. universe.py에서 종목 목록을 받아온다.
2. yfinance로 가격 데이터를 다운로드한다.
3. 종목별 Parquet 파일로 저장한다.
4. 이미 저장된 데이터는 다시 받지 않는다.
5. 로그를 남긴다.

작성자 : 사용자 + ChatGPT
"""

# =====================================================
# 필요한 라이브러리 불러오기
# =====================================================

from pathlib import Path
from datetime import datetime, timedelta
import logging
import time

import pandas as pd
import yfinance as yf

# universe.py에서 만든 함수
from .universe import get_universe


# =====================================================
# 프로젝트 폴더 설정
# =====================================================

# 현재 파일(src)에 있는 위치를 기준으로
# 프로젝트 최상위 폴더를 찾는다.
BASE_DIR = Path(__file__).resolve().parent.parent

# 데이터 저장 폴더
RAW_DIR = BASE_DIR / "data" / "raw" / "prices"

# 로그 저장 폴더
LOG_DIR = BASE_DIR / "logs"

# 실패한 종목 저장
FAILED_FILE = LOG_DIR / "failed_tickers.txt"

# 로그 파일
LOG_FILE = LOG_DIR / "download.log"


# =====================================================
# 폴더 자동 생성
# =====================================================

# exist_ok=True
# 이미 폴더가 있어도 에러를 내지 않는다.

RAW_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================
# Logger 설정
# =====================================================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# =====================================================
# 다운로드 기간
# =====================================================

# 오늘 날짜
END_DATE = datetime.today()

# 2년 전
START_DATE = END_DATE - timedelta(days=730)

# yfinance에서 사용하는 문자열 형식
START_DATE = START_DATE.strftime("%Y-%m-%d")
END_DATE = END_DATE.strftime("%Y-%m-%d")


# =====================================================
# 다운로드 설정
# =====================================================

# 한 번에 몇 개 종목을 받을지
# (너무 크면 오류가 날 수 있다.)
BATCH_SIZE = 25

# 다운로드 실패 시 최대 재시도 횟수
MAX_RETRY = 3


# =====================================================
# 시작 메시지
# =====================================================

print("=" * 60)
print("Price Collector 시작")
print("=" * 60)

logger.info("========== Price Collector Start ==========")

# =====================================================
# 파일 관련 함수
# =====================================================

def get_file_path(ticker: str) -> Path:
    """
    종목 티커에 해당하는 Parquet 파일 경로를 반환한다.

    예)
    ticker = "AAPL"

    반환값
    data/raw/prices/AAPL.parquet
    """

    # ticker는 대문자로 통일한다.
    ticker = ticker.upper()

    return RAW_DIR / f"{ticker}.parquet"


# =====================================================
# 기존 데이터 불러오기
# =====================================================

def load_existing_data(ticker: str) -> pd.DataFrame | None:
    """
    이미 저장된 Parquet 파일이 있으면 불러온다.

    파일이 없으면 None을 반환한다.
    """

    file_path = get_file_path(ticker)

    # 파일이 없는 경우
    if not file_path.exists():
        return None

    try:
        df = pd.read_parquet(file_path)

        # 날짜순으로 정렬
        df = df.sort_index()

        return df

    except Exception as e:

        logger.error(f"{ticker} 읽기 실패 : {e}")

        return None


# =====================================================
# 다운로드 시작 날짜 결정
# =====================================================

def get_download_start_date(existing_df: pd.DataFrame | None) -> str:
    """
    다운로드를 언제부터 시작할지 결정한다.

    경우 1
    기존 파일 없음

    →
    2년 전부터 다운로드

    경우 2
    기존 파일 있음

    →
    마지막 날짜의 다음날부터 다운로드
    """

    # 처음 다운로드하는 경우
    if existing_df is None:

        return START_DATE

    # 마지막 저장 날짜
    last_date = existing_df.index.max()

    # 하루 더한다.
    next_date = last_date + timedelta(days=1)

    return next_date.strftime("%Y-%m-%d")
    
# =====================================================
# 티커 리스트를 여러 개의 작은 그룹으로 나누기
# =====================================================

def split_batches(tickers: list[str], batch_size: int = BATCH_SIZE):
    """
    긴 티커 리스트를 batch_size개씩 나누어 반환한다.

    예)
    [AAPL, MSFT, NVDA, META]

    →

    [AAPL, MSFT]
    [NVDA, META]
    """

    for i in range(0, len(tickers), batch_size):

        yield tickers[i:i + batch_size]


# =====================================================
# 배치 다운로드
# =====================================================

def download_batch(
    tickers: list[str],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """
    여러 종목을 한 번에 다운로드한다.
    """

    df = yf.download(

        tickers=tickers,

        start=start_date,

        end=end_date,

        auto_adjust=False,

        progress=False,

        group_by="ticker",

        threads=True,
    )

    return df


# =====================================================
# 배치 데이터에서 종목 하나만 꺼내기
# =====================================================

def extract_single_ticker(
    batch_df: pd.DataFrame,
    ticker: str,
) -> pd.DataFrame:
    """
    MultiIndex DataFrame에서
    하나의 종목만 추출한다.
    """

    try:

        # 여러 종목 다운로드인 경우
        if isinstance(batch_df.columns, pd.MultiIndex):

            df = batch_df[ticker].copy()

        else:

            # 종목이 1개뿐이면 MultiIndex가 아니다.
            df = batch_df.copy()

        # 비어있는 데이터 제거
        df = df.dropna(how="all")

        return df

    except Exception as e:

        logger.error(f"{ticker} 추출 실패 : {e}")

        return pd.DataFrame()

        # =====================================================
# 전체 다운로드 실행
# =====================================================

def download_prices():
    """
    전체 종목의 가격 데이터를 다운로드하고 저장한다.
    """

    # Universe 불러오기
    universe = get_universe("both")

    # ticker 컬럼을 리스트로 변환
    tickers = universe["ticker"].tolist()

    logger.info(f"총 {len(tickers)}개 종목")

    print(f"\n총 {len(tickers)}개 종목 다운로드 시작\n")

    total_saved = 0
    total_failed = 0

    # 25개씩 나누기
    for batch_no, batch in enumerate(split_batches(tickers), start=1):

        print(f"\n========== Batch {batch_no} ==========")

        try:

            batch_df = download_batch(
                batch,
                START_DATE,
                END_DATE,
            )

        except Exception as e:

            logger.error(f"Batch {batch_no} 실패 : {e}")

            total_failed += len(batch)

            continue

        # 종목 하나씩 처리
        for ticker in batch:

            try:

                df = extract_single_ticker(
                    batch_df,
                    ticker,
                )

                # 데이터가 비었으면 넘어감
                if df.empty:

                    logger.warning(f"{ticker} 데이터 없음")

                    total_failed += 1

                    continue

                # 저장
                save_price_data(
                    ticker,
                    df,
                )

                total_saved += 1

                print(
                    f"✔ {ticker:<6} ({len(df)} rows)"
                )

            except Exception as e:

                logger.error(f"{ticker} 실패 : {e}")

                total_failed += 1

    print("\n==============================")
    print("다운로드 완료")
    print("==============================")
    print(f"성공 : {total_saved}")
    print(f"실패 : {total_failed}")

            
          
# =====================================================
# 데이터 저장
# =====================================================

def save_price_data(
    ticker: str,
    new_df: pd.DataFrame,
) -> None:
    """
    다운로드한 데이터를 Parquet 파일로 저장한다.

    이미 저장된 데이터가 있으면
    기존 데이터와 합친 뒤
    중복을 제거하고 다시 저장한다.
    """

    # 빈 데이터는 저장하지 않는다.
    if new_df.empty:

        logger.warning(f"{ticker} : 저장할 데이터가 없습니다.")

        return

    # 저장할 파일 위치
    file_path = get_file_path(ticker)

    # 기존 데이터 읽기
    old_df = load_existing_data(ticker)

    # 기존 데이터가 있으면 합친다.
    if old_df is not None:

        new_df = pd.concat(
            [old_df, new_df]
        )

        # 같은 날짜가 두 번 있으면
        # 마지막 데이터를 남긴다.
        new_df = new_df[~new_df.index.duplicated(
            keep="last"
        )]

    # 날짜순 정렬
    new_df = new_df.sort_index()

    # 저장
    new_df.to_parquet(file_path)

    logger.info(
        f"{ticker} 저장 완료 ({len(new_df)} rows)"
    )