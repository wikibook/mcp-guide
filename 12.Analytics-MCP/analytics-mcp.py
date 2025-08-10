from fastmcp import FastMCP
import pandas as pd
from typing import Annotated
from pydantic import Field

# CSV 파일 경로
_df_cache = {}
csv_path = "C:\\MCP_Test\\wikidocs-mcp\\Analytics-MCP\\data.csv"
_df_cache["df"] = pd.read_csv(csv_path)

# MCP 인스턴스 생성
mcp = FastMCP(name="Analytics-MCP", dependencies=["pandas"])

# DataFrame을 캐시에서 불러오는 함수
@mcp.tool(
    name="load_df",
    description="Load the DataFrame from the cache."
)
def load_df():
    """
    Args:
        None

    Returns:
        The DataFrame loaded from the cache.
    """
    if "df" not in _df_cache:
        raise ValueError("No DataFrame found in cache. Please save a DataFrame with save_df first.")
    return _df_cache["df"]


# DataFrame의 기본 정보(shape, dtypes 등)를 확인하는 함수
@mcp.tool(
    name="basic_data_check",
    description="Run a basic data check operation on the cached DataFrame. Supported operations: shape, dtypes, missing, columns, describe"
)
def basic_data_check(
    operation: Annotated[str, Field(description="The kind of basic data check to perform (shape, dtypes, missing, columns, describe).")]
):
    """
    Args:
        operation (str): The kind of basic data check to perform (one of "shape", "dtypes", "missing", "columns", "describe")

    Returns:
        The result of the requested data check operation.
    """
    df = _df_cache["df"]
    operations = {
        "shape": lambda: df.shape,
        "dtypes": lambda: df.dtypes,
        "missing": lambda: df.isnull().sum(),
        "columns": lambda: list(df.columns),
        "describe": lambda: df.describe()
    }
    if operation not in operations:
        raise ValueError(f"Unsupported operation: {operation}")
    return operations[operation]()


# 컬럼 데이터 확인(고유값, 값별 개수) 함수
@mcp.tool(
    name="column_data_check",
    description="Run a column-specific data check operation on the cached DataFrame. Supported operations: unique, value_counts"
)
def column_data_check(
    operation: Annotated[str, Field(description="The kind of column data check to perform (unique, value_counts).")],
    column: Annotated[str, Field(description="The name of the column to operate on.")]
):
    """
    Args:
        operation (str): The operation to perform on the column (one of "unique", "value_counts")
        column (str): The name of the column to operate on

    Returns:
        The unique values or value counts of the column
    """
    df = _df_cache["df"]
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in DataFrame.")
    operations = {
        "unique": lambda: df[column].unique(),
        "value_counts": lambda: df[column].value_counts()
    }
    if operation not in operations:
        raise ValueError(f"Unsupported operation: {operation}")
    return operations[operation]()


# 데이터 전처리(결측치 제거, 중복 제거) 함수
@mcp.tool(
    name="data_preprocess",
    description="Run a basic data preprocessing operation on the cached DataFrame and update the cache. Supported operations: dropna, drop_duplicates"
)
def data_preprocess(
    operation: Annotated[str, Field(description="The preprocessing operation to perform (dropna, drop_duplicates).")]
):
    """
    Args:
        operation (str): The preprocessing operation to perform (one of "dropna", "drop_duplicates")

    Returns:
        The DataFrame after preprocessing, updated in the cache.
    """
    df = _df_cache["df"]
    operations = {
        "dropna": lambda: df.dropna(),
        "drop_duplicates": lambda: df.drop_duplicates()
    }
    if operation not in operations:
        raise ValueError(f"Unsupported operation: {operation}")
    result = operations[operation]()
    _df_cache["df"] = result
    return result


# 컬럼 기반 데이터 필터링(크다, 같다, 작다) 함수
@mcp.tool(
    name="col_data_analysis",
    description="Column-based data analysis. Supported operations: filter_gt (greater than), filter_eq (equal to), filter_lt (less than)"
)
def col_data_analysis(
    operation: Annotated[str, Field(description="The filtering operation to perform (filter_gt, filter_eq, filter_lt).")],
    column: Annotated[str, Field(description="The name of the column to filter.")],
    condition_value: Annotated[int, Field(description="The value to compare against.")]
):
    """
    Args:
        operation (str): The filtering operation to perform (one of "filter_gt", "filter_eq", "filter_lt")
        column (str): The name of the column to filter
        condition_value (int): The value to compare against

    Returns:
        The filtered DataFrame
    """
    df = _df_cache["df"]
    operations = {
        "filter_gt": lambda: df[df[column] > condition_value],
        "filter_eq": lambda: df[df[column] == condition_value],
        "filter_lt": lambda: df[df[column] < condition_value]
    }
    if operation not in operations:
        raise ValueError(f"Unsupported operation: {operation}")
    return operations[operation]()


# 그룹 기반 데이터 집계(평균, 최대, 합계, 개수) 함수
@mcp.tool(
    name="group_data_analysis",
    description="Group-based data analysis. Supported operations: mean, max, sum, count"
)
def group_data_analysis(
    operation: Annotated[str, Field(description="The aggregation operation to perform (mean, max, sum, count).")],
    group_column: Annotated[str, Field(description="The name of the column to group by.")],
    target_column: Annotated[str, Field(description="The name of the column to aggregate.")]
):
    """
    Args:
        operation (str): The aggregation operation to perform (one of "mean", "max", "sum", "count")
        group_column (str): The name of the column to group by
        target_column (str): The name of the column to aggregate

    Returns:
        The result of the group-based aggregation
    """
    df = _df_cache["df"]
    operations = {
        "mean": lambda: df.groupby(group_column)[target_column].mean(),
        "max": lambda: df.groupby(group_column)[target_column].max(),
        "sum": lambda: df.groupby(group_column)[target_column].sum(),
        "count": lambda: df.groupby(group_column)[target_column].count()
    }
    if operation not in operations:
        raise ValueError(f"Unsupported operation: {operation}")
    return operations[operation]()

if __name__ == "__main__":
    mcp.run()
