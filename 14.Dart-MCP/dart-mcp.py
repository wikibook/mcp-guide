import OpenDartReader
import pandas as pd
import os
from fastmcp import FastMCP
from typing import Annotated, Literal
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()

mcp=FastMCP("Dart-MCP",dependencies=["pandas","requests","OpenDartReader","pydantic"])
dart = OpenDartReader(os.environ.get("DART_API_KEY"))

REPORT_CODES = [
    '조건부자본증권미상환', '미등기임원보수', '회사채미상환', '단기사채미상환', '기업어음미상환',
    '채무증권발행', '사모자금사용', '공모자금사용', '임원전체보수승인', '임원전체보수유형',
    '주식총수', '회계감사', '감사용역', '회계감사용역계약', '사외이사', '신종자본증권미상환',
    '증자', '배당', '자기주식', '최대주주', '최대주주변동', '소액주주', '임원', '직원',
    '임원개인보수', '임원전체보수', '개인별보수', '타법인출자'
]
EVENT_CODES = [
    '부도발생', '영업정지', '회생절차', '해산사유', '유상증자', '무상증자', '유무상증자', '감자',
    '관리절차개시', '소송', '해외상장결정', '해외상장폐지결정', '해외상장', '해외상장폐지',
    '전환사채발행', '신주인수권부사채발행', '교환사채발행', '관리절차중단', '조건부자본증권발행',
    '자산양수도', '타법인증권양도', '유형자산양도', '유형자산양수', '타법인증권양수', '영업양도',
    '영업양수', '자기주식취득신탁계약해지', '자기주식취득신탁계약체결', '자기주식처분', '자기주식취득',
    '주식교환', '회사분할합병', '회사분할', '회사합병', '사채권양수', '사채권양도결정'
]

# 0. 기업명으로 고유번호 얻기
@mcp.tool(name="get_corp_code",description="Fetch the corporate code of a company.")
def get_corp_code(
    corp_name: Annotated[str, Field(description="Corporate name of the company.")]
):
    """
    MCP tool for fetching a company's corporate code.
    Args:
        corp_name (str): Corporate name of the company.
    Returns:
        str: Corporate code of the company.
    """
    return dart.find_corp_code(corp_name)

# 1. 공시정보 - 기업개황 : 기업의 개황정보
@mcp.tool(name="get_company_overview",description="Fetch the general overview information of a company.")
def get_company_overview(
    corp_code: Annotated[str, Field(description="Corporate code of the company.")]
):
    """
    MCP tool for fetching a company's overview information.
    Args:
        corp_code (str): Corporate code of the company.
    Returns:
        dict: Company overview information.
    """
    return dart.company(corp_code)

# 2. 기업의 주요계정과목(재무상태표, 손익계산서) , 안됨 
@mcp.tool(name="get_financial_statement",description="Fetch the company's main financial statement items (Balance Sheet or Income Statement).")
def get_financial_statement(
    corp_code: Annotated[str, Field(description="Corporate code of the company.")],
    date: Annotated[str, Field(description="Year in 'yyyy' format.")],
    report_code: Annotated[str, Field(description="Report code: '11012' for Semi-Annual, '11014' for Q3, '11013' for Q1.")],
    sj_div: Annotated[Literal['BS', 'IS'], Field(description="Statement type: 'BS' for Balance Sheet, 'IS' for Income Statement.")]
):
    """
    MCP tool for fetching financial statement information.
    Args:
        corp_code (str): Corporate code of the company.
        date (str): Year in 'yyyy' format.
        report_code (str): Report code for the statement period.
        sj_div (str): Statement type ('BS' or 'IS').

    Returns:
        DataFrame: Filtered financial statement data.
    """
    df = dart.finstate(corp_code, date, report_code)
    filtered_df = df[(df['fs_div'] == 'CFS') & (df['sj_div'] == sj_div)]
    if filtered_df.empty:
        filtered_df = df[(df['fs_div'] == 'OFS') & (df['sj_div'] == sj_div)]
    filtered_df = filtered_df[["corp_code", "bsns_year", "reprt_code", "account_nm", "thstrm_amount"]]
    return filtered_df

# 3. 사업보고서 
@mcp.tool(
    name="get_specific_business_report",
    description="Fetch a specific type of business report for a company."
)
def get_specific_business_report(
    corp_code: Annotated[str, Field(description="Corporate code of the company.")],
    report_code: Annotated[str, Field(description=f"Report code. Must be one of: {REPORT_CODES}")],
    date: Annotated[str, Field(description="Year in 'yyyy' format.")]
):
    """
    MCP tool for fetching a specific type of business report.

    Args:
        corp_code (str): Corporate code of the company.
        date (str): Year in 'yyyy' format.
        report_code (str): Report code (must be one of the predefined values).

    Returns:
        dict or DataFrame: Business report information, or error message if report_code is invalid or no data found.
    """
    if report_code not in REPORT_CODES:
        return {"error": f"report_code must be one of: {REPORT_CODES}"}

    result = dart.report(corp_code, report_code, date)
    
    if isinstance(result, pd.DataFrame) and result.empty:
        return {"message": "No data found for the given parameters."}

    return result

# 4. 주요사항보고서
@mcp.tool(
    name="get_major_event_report",
    description="Fetch a major event report for a company."
)
def get_major_event_report(
    corp_code: Annotated[str, Field(description="Corporate code of the company.")],
    event: Annotated[str, Field(description=f"Event code. Must be one of: {EVENT_CODES}")],
    date: Annotated[str, Field(description="Year in 'yyyy' format.")]
):
    """
    MCP tool for fetching a major event report.

    Args:
        corp_code (str): Corporate code of the company.
        event (str): Event code (must be one of the predefined values).
        date (str): Year in 'yyyy' format.

    Returns:
        dict or DataFrame: Major event report information, or error message if event is invalid or no data found.
    """
    if event not in EVENT_CODES:
        return {"error": f"event must be one of: {EVENT_CODES}"}

    result = dart.event(corp_code, event, date)

    if isinstance(result, pd.DataFrame) and result.empty:
        return {"message": "No data found for the given parameters."}
    return result

if __name__ == '__main__':
    mcp.run()
