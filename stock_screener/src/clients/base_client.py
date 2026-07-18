"""
base_client.py

모든 API Client가 공통으로 사용하는
기본 클래스(Base Class).

현재는 FMP에서 사용하지만,
나중에 SEC, Finnhub 등도
이 클래스를 상속받아 사용할 수 있다.
"""

# =====================================================
# 필요한 라이브러리
# =====================================================

import requests


class BaseClient:
    """
    모든 API Client의 부모 클래스
    """

    def __init__(self):

        # requests.Session()

        # 인터넷 연결을 계속 재사용해서
        # 속도를 높여준다.
        self.session = requests.Session()

    def get(
        self,
        url: str,
        params: dict | None = None,
    ) -> dict:
        """
        GET 요청을 보내고
        JSON 데이터를 반환한다.
        """

        response = self.session.get(

            url,

            params=params,

            timeout=30,
        )

        # 404
        # 500
        # 등을 자동으로 Exception 발생

        response.raise_for_status()

        return response.json()