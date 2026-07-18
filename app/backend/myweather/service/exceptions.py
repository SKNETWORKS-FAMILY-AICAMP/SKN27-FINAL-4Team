class WeatherServiceError(Exception):
    """외부 날씨 서비스 처리 중 발생한 오류."""


class WeatherInputError(WeatherServiceError):
    """날씨 조회 입력값이 유효하지 않을 때 발생하는 오류."""

