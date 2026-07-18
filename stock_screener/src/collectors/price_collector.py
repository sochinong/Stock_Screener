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
BATCH_SIZE = 50

# 다운로드 실패 시 최대 재시도 횟수
MAX_RETRY = 3


# =====================================================
# 시작 메시지
# =====================================================

print("=" * 60)
print("Price Collector 시작")
print("=" * 60)

logger.info("========== Price Collector Start ==========")