import requests
from fastmcp import FastMCP

mcp = FastMCP("Weather-MCP", dependencies=["requests"])

def get_lat_lon_from_ip():
    try:
        res = requests.get('https://ipinfo.io/json')
        data = res.json()
        loc = data.get('loc', '37.5665,126.9780')  # 기본값: 서울
        latitude, longitude = map(float, loc.split(','))
        return latitude, longitude
    except Exception as e:
        print(f"위치 정보를 가져올 수 없습니다. 기본값(서울) 사용. 오류: {e}")
        return 37.5665, 126.9780  # 기본값: 서울

@mcp.tool(
    name="get_weather",
    description="Get current weather information using Open-Meteo API based on your IP."
)
def get_weather():
    """Get weather information using Open-Meteo API."""
    latitude, longitude = get_lat_lon_from_ip()
    url = f'https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,weather_code&timezone=GMT&forecast_days=1'
    try:
        response = requests.get(url)
        weather_data = response.json()
        return weather_data
    except Exception as e:
        print("날씨 정보 요청 오류:", e)
        return None

if __name__ == "__main__":
    mcp.run()