import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from typing import Annotated
from pydantic import Field
import pandas as pd

# 환경변수 로드
load_dotenv()

mcp = FastMCP(name="KIStock-MCP",dependencies=["httpx","pydantic","pandas"])

class KISAuthManager:
    # 실전/모의투자 도메인 및 경로
    DOMAIN = "https://openapi.koreainvestment.com:9443"
    VIRTUAL_DOMAIN = "https://openapivts.koreainvestment.com:29443"
    TOKEN_PATH = "/oauth2/tokenP"
    HASHKEY_PATH = "/uapi/hashkey"
    CONTENT_TYPE = "application/json"
    AUTH_TYPE = "Bearer"
    TOKEN_FILE = Path(__file__).resolve().parent / "token.json"

    # 실전/모의투자 TR_ID
    REAL_TR = {
        "price": "FHKST01010100",
        "balance": "TTTC8434R",
        "buy": "TTTC0802U",
        "sell": "TTTC0801U",
        "order_list": "TTTC8001R",
        "stock_ask": "FHKST01010200",
        "stock_info": "FHKST01010400",
    }
    VIRTUAL_TR = {
        "price": "FHKST01010100",
        "balance": "VTTC8434R",
        "buy": "VTTC0802U",
        "sell": "VTTC0801U",
        "order_list": "VTTC8001R",
        "order_detail": "VTTC80362R",
        "stock_info": "FHKST01010400",
        "stock_ask": "FHKST01010200",
    }

    @classmethod
    def is_real(cls):
        return os.environ.get("KIS_ACCOUNT_TYPE", "REAL").upper() == "REAL"

    @classmethod
    def get_domain(cls):
        return cls.DOMAIN if cls.is_real() else cls.VIRTUAL_DOMAIN

    @classmethod
    def get_tr_id(cls, key):
        return cls.REAL_TR.get(key) if cls.is_real() else cls.VIRTUAL_TR.get(key)

    @classmethod
    def load_token(cls):
        if cls.TOKEN_FILE.exists():
            try:
                with open(cls.TOKEN_FILE, 'r') as f:
                    token_data = json.load(f)
                    expires_at = datetime.fromisoformat(token_data['expires_at'])
                    if datetime.now() < expires_at:
                        return token_data['token'], expires_at
            except Exception as e:
                print(f"Error loading token: {e}", file=sys.stderr)
        return None, None

    @classmethod
    def save_token(cls, token: str, expires_at: datetime):
        try:
            with open(cls.TOKEN_FILE, 'w') as f:
                json.dump({'token': token, 'expires_at': expires_at.isoformat()}, f)
        except Exception as e:
            print(f"Error saving token: {e}", file=sys.stderr)

    @classmethod
    async def get_access_token(cls, client: httpx.AsyncClient) -> str:
        token, expires_at = cls.load_token()
        if token and expires_at and datetime.now() < expires_at:
            return token
        token_response = await client.post(
            f"{cls.get_domain()}{cls.TOKEN_PATH}",
            headers={"content-type": cls.CONTENT_TYPE},
            json={
                "grant_type": "client_credentials",
                "appkey": os.environ["KIS_APP_KEY"],
                "appsecret": os.environ["KIS_APP_SECRET"]
            }
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        token = token_data["access_token"]
        expires_at = datetime.now() + timedelta(hours=23)
        cls.save_token(token, expires_at)
        return token

    @classmethod
    async def get_hashkey(cls, client: httpx.AsyncClient, token: str, body: dict) -> str:
        response = await client.post(
            f"{cls.get_domain()}{cls.HASHKEY_PATH}",
            headers={
                "content-type": cls.CONTENT_TYPE,
                "authorization": f"{cls.AUTH_TYPE} {token}",
                "appkey": os.environ["KIS_APP_KEY"],
                "appsecret": os.environ["KIS_APP_SECRET"],
            },
            json=body
        )
        response.raise_for_status()
        return response.json()["HASH"]

# MCP TOOL: 현재가 조회
@mcp.tool(
    name="get_stock_price",
    description="Fetch the current price information for a given stock symbol."
)
async def get_stock_price(
    symbol: Annotated[str, Field(description="Stock symbol (6 digits)")]
) -> dict:
    """
    MCP tool for fetching current stock price.
    Returns error message if no data found.
    """
    STOCK_PRICE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-price"
    async with httpx.AsyncClient() as client:
        token = await KISAuthManager.get_access_token(client)
        response = await client.get(
            f"{KISAuthManager.get_domain()}{STOCK_PRICE_PATH}",
            headers={
                "content-type": KISAuthManager.CONTENT_TYPE,
                "authorization": f"{KISAuthManager.AUTH_TYPE} {token}",
                "appkey": os.environ["KIS_APP_KEY"],
                "appsecret": os.environ["KIS_APP_SECRET"],
                "tr_id": KISAuthManager.get_tr_id("price")
            },
            params={
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": symbol
            }
        )
        response.raise_for_status()
        data = response.json().get("output")
        if not data or (isinstance(data, dict) and not data):
            return {"message": "No data found for the given symbol."}
        keys = [
            "stck_shrn_iscd", "rprs_mrkt_kor_name", "bstp_kor_isnm", "stck_prpr", "prdy_vrss", "prdy_ctrt",
            "stck_oprc", "stck_hgpr", "stck_lwpr", "acml_vol", "acml_tr_pbmn", "per", "pbr",
            "eps", "bps", "hts_frgn_ehrt", "frgn_ntby_qty", "pgtr_ntby_qty"
        ]
        return {key: data.get(key) for key in keys}

# MCP TOOL: 잔고 조회
@mcp.tool(
    name="get_account_balance",
    description="Fetch the current account balance."
)
async def get_account_balance() -> dict:
    """
    MCP tool for fetching account balance.
    Returns error message if no data found.
    """
    BALANCE_PATH = "/uapi/domestic-stock/v1/trading/inquire-balance"
    async with httpx.AsyncClient() as client:
        token = await KISAuthManager.get_access_token(client)
        params = {
            "CANO": os.environ["KIS_CANO"],
            "ACNT_PRDT_CD": "01",
            "AFHR_FLPR_YN": "N",
            "INQR_DVSN": "01",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
            "OFL_YN": ""
        }
        response = await client.get(
            f"{KISAuthManager.get_domain()}{BALANCE_PATH}",
            headers={
                "content-type": KISAuthManager.CONTENT_TYPE,
                "authorization": f"{KISAuthManager.AUTH_TYPE} {token}",
                "appkey": os.environ["KIS_APP_KEY"],
                "appsecret": os.environ["KIS_APP_SECRET"],
                "tr_id": KISAuthManager.get_tr_id("balance")
            },
            params=params
        )
        response.raise_for_status()
        data = response.json()
        if not data or "output1" not in data or not data["output1"]:
            return {"message": "No balance data found."}

        # 추출할 컬럼 리스트
        output1_keys = [
            "pdno", "prdt_name", "hldg_qty", "ord_psbl_qty", "pchs_avg_pric",
            "prpr", "evlu_amt", "evlu_pfls_amt", "evlu_pfls_rt"
        ]
        output2_keys = [
            "dnca_tot_amt", "scts_evlu_amt", "tot_evlu_amt", "nass_amt",
            "evlu_pfls_smtl_amt", "asst_icdc_amt", "asst_icdc_erng_rt"
        ]

        # output1(보유 종목)에서 필요한 컬럼만 추출
        filtered_output1 = [
            {key: item.get(key) for key in output1_keys}
            for item in data.get("output1", [])
        ]

        # output2(계좌 요약)에서 필요한 컬럼만 추출
        filtered_output2 = [
            {key: item.get(key) for key in output2_keys}
            for item in data.get("output2", [])
        ]

        return {
            "output1": filtered_output1,
            "output2": filtered_output2
        }


# MCP TOOL: 매수/매도 주문
@mcp.tool(
    name="place_order",
    description="Place a buy or sell order for a stock."
)
async def place_order(
    symbol: Annotated[str, Field(description="Stock symbol (6 digits)")],
    quantity: Annotated[int, Field(description="Order quantity")],
    price: Annotated[int, Field(description="Order price (0 for market order)")],
    order_type: Annotated[str, Field(description="'buy' or 'sell'")]
) -> dict:
    """
    MCP tool for placing a buy or sell order.
    Returns error message if order_type is invalid or order fails.
    """
    ORDER_PATH = "/uapi/domestic-stock/v1/trading/order-cash"
    order_type = order_type.lower()
    if order_type not in ["buy", "sell"]:
        return {"error": "order_type must be either 'buy' or 'sell'."}
    async with httpx.AsyncClient() as client:
        token = await KISAuthManager.get_access_token(client)
        request_data = {
            "CANO": os.environ["KIS_CANO"],
            "ACNT_PRDT_CD": "01",
            "PDNO": symbol,
            "ORD_DVSN": "01" if price == 0 else "00",
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price),
        }
        hashkey = await KISAuthManager.get_hashkey(client, token, request_data)
        response = await client.post(
            f"{KISAuthManager.get_domain()}{ORDER_PATH}",
            headers={
                "content-type": KISAuthManager.CONTENT_TYPE,
                "authorization": f"{KISAuthManager.AUTH_TYPE} {token}",
                "appkey": os.environ["KIS_APP_KEY"],
                "appsecret": os.environ["KIS_APP_SECRET"],
                "tr_id": KISAuthManager.get_tr_id(order_type),
                "hashkey": hashkey
            },
            json=request_data
        )
        response.raise_for_status()
        data = response.json()
        if not data or "output" not in data:
            return {"message": "Order failed or no response."}
        return data

# MCP TOOL: 주문내역 조회
@mcp.tool(
    name="get_order_list",
    description="Fetch the order history for a given date range."
)
async def get_order_list(
    start_date: Annotated[str, Field(description="Start date (YYYYMMDD)")],
    end_date: Annotated[str, Field(description="End date (YYYYMMDD)")]
) -> dict:
    """
    MCP tool for fetching order list.
    Returns error message if no data found.
    """
    ORDER_LIST_PATH = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
    async with httpx.AsyncClient() as client:
        token = await KISAuthManager.get_access_token(client)
        params = {
            "CANO": os.environ["KIS_CANO"],
            "ACNT_PRDT_CD": "01",
            "INQR_STRT_DT": start_date,
            "INQR_END_DT": end_date,
            "SLL_BUY_DVSN_CD": "00",
            "INQR_DVSN": "00",
            "PDNO": "",
            "CCLD_DVSN": "00",
            "ORD_GNO_BRNO": "",
            "ODNO": "",
            "INQR_DVSN_3": "00",
            "INQR_DVSN_1": "",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        response = await client.get(
            f"{KISAuthManager.get_domain()}{ORDER_LIST_PATH}",
            headers={
                "content-type": KISAuthManager.CONTENT_TYPE,
                "authorization": f"{KISAuthManager.AUTH_TYPE} {token}",
                "appkey": os.environ["KIS_APP_KEY"],
                "appsecret": os.environ["KIS_APP_SECRET"],
                "tr_id": KISAuthManager.get_tr_id("order_list")
            },
            params=params
        )
        response.raise_for_status()
        data = response.json()
        if not data or "output1" not in data or not data["output1"]:
            return {"message": "No order history found for the given period."}
        # 중요한 컬럼만 추출
        important_columns = [
            "ord_dt", "odno", "ord_dvsn_name", "sll_buy_dvsn_cd_name",
            "pdno", "prdt_name", "ord_qty", "ord_unpr",
            "tot_ccld_qty", "avg_prvs", "tot_ccld_amt",
            "cncl_yn", "rmn_qty", "rjct_qty"
        ]
        filtered_output1 = []
        for item in data["output1"]:
            filtered_item = {key: item[key] for key in important_columns if key in item}
            filtered_output1.append(filtered_item)
        # output2는 그대로 반환
        result = {
            "output1": filtered_output1,
            "output2": data.get("output2", {}),
            "rt_cd": data.get("rt_cd", ""),
            "msg_cd": data.get("msg_cd", ""),
            "msg1": data.get("msg1", "")
        }
        return result

# MCP TOOL: 호가 조회
@mcp.tool(
    name="get_stock_ask_price",
    description="Fetch the ask/bid price for a stock."
)
async def get_stock_ask_price(
    symbol: Annotated[str, Field(description="Stock symbol (6 digits)")]
) -> dict:
    """
    MCP tool for fetching stock ask/bid price.
    Returns error message if no data found.
    """
    STOCK_ASK_PATH = "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn"
    async with httpx.AsyncClient() as client:
        token = await KISAuthManager.get_access_token(client)
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol,
        }
        response = await client.get(
            f"{KISAuthManager.get_domain()}{STOCK_ASK_PATH}",
            headers={
                "content-type": KISAuthManager.CONTENT_TYPE,
                "authorization": f"{KISAuthManager.AUTH_TYPE} {token}",
                "appkey": os.environ["KIS_APP_KEY"],
                "appsecret": os.environ["KIS_APP_SECRET"],
                "tr_id": KISAuthManager.get_tr_id("stock_ask")
            },
            params=params
        )
        if response.status_code != 200:
            raise Exception(f"Failed to get stock ask price: {response.text}")
        data = response.json()
        # 핵심 컬럼만 추출
        output1_keys = [
            "askp1", "askp_rsqn1", "bidp1", "bidp_rsqn1", "total_askp_rsqn", "total_bidp_rsqn"
        ]
        output2_keys = [
            "stck_prpr", "stck_oprc", "stck_hgpr", "stck_lwpr", "stck_sdpr", "stck_shrn_iscd"
        ]
        filtered_output1 = {key: data.get("output1", {}).get(key) for key in output1_keys}
        filtered_output2 = {key: data.get("output2", {}).get(key) for key in output2_keys}
        return {
            "output1": filtered_output1,
            "output2": filtered_output2
        }

# MCP TOOL: 일별주가 조회
@mcp.tool(
    name="get_daily_price",
    description="Fetch daily price data for a stock."
)
async def get_daily_price(
    symbol: Annotated[str, Field(description="Stock symbol (6 digits)")],
    start_date: Annotated[str, Field(description="Start date (YYYYMMDD)")],
    end_date: Annotated[str, Field(description="End date (YYYYMMDD)")],
    adj: Annotated[str, Field(description="Adjusted price (0: no, 1: yes), default 0")] = "0"
) -> dict:
    """
    MCP tool for fetching daily price data.
    Returns error message if no data found.
    """
    STOCK_INFO_PATH = "/uapi/domestic-stock/v1/quotations/inquire-daily-price"
    async with httpx.AsyncClient() as client:
        token = await KISAuthManager.get_access_token(client)
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": symbol,
            "fid_org_adj_prc": adj,
            "fid_period_div_code": "D",
            "fid_begin_date": start_date,
            "fid_end_date": end_date
        }
        response = await client.get(
            f"{KISAuthManager.get_domain()}{STOCK_INFO_PATH}",
            headers={
                "content-type": KISAuthManager.CONTENT_TYPE,
                "authorization": f"{KISAuthManager.AUTH_TYPE} {token}",
                "appkey": os.environ["KIS_APP_KEY"],
                "appsecret": os.environ["KIS_APP_SECRET"],
                "tr_id": KISAuthManager.get_tr_id("stock_info")
            },
            params=params
        )
        if response.status_code != 200:
            raise Exception(f"Failed to get daily price: {response.text}")
        data = response.json()
        # 일별 데이터에서 진짜 핵심 컬럼만 추출
        core_keys = ["stck_bsop_date", "stck_oprc", "stck_hgpr", "stck_lwpr", "stck_clpr"]
        filtered_output = [
            {key: item.get(key) for key in core_keys}
            for item in data.get("output", [])
        ]
        return filtered_output

if __name__ == "__main__":
    mcp.run()