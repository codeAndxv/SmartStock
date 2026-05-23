"""Scan today's limit-up stocks and predict tomorrow's movement."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Generator, List, Tuple

import akshare as ak
import pandas as pd

from .stock_info import _to_sina_symbol


@dataclass
class Prediction:
    """Limit-up stock with prediction."""
    code: str
    name: str
    price: float
    today_change: float
    predicted_change: float
    industry: str
    ytd_change: float
    score: int


def _get_year_start_price(stock_code: str) -> float:
    """
    Get the first available close price of the year for YTD calculation.

    Args:
        stock_code: Bare stock code, e.g. "000001"

    Returns:
        First close price of the year

    Raises:
        ValueError: If data cannot be fetched
    """
    sina_symbol = _to_sina_symbol(stock_code)
    year = date.today().year
    start = date(year, 1, 1)
    end = date(year, 1, 20)

    try:
        df = ak.stock_zh_a_daily(
            symbol=sina_symbol,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
        )
    except Exception as e:
        raise ValueError(f"Failed to fetch year-start price for {stock_code}: {e}") from e

    if df.empty:
        raise ValueError(f"No year-start data for {stock_code}")

    return float(df.iloc[0]["close"])


def _get_recent_bars(stock_code: str, days: int) -> pd.DataFrame:
    """
    Get recent N trading days as a DataFrame.

    Args:
        stock_code: Bare stock code, e.g. "000001"
        days: Number of calendar days to look back

    Returns:
        DataFrame with OHLCV columns

    Raises:
        ValueError: If data cannot be fetched
    """
    sina_symbol = _to_sina_symbol(stock_code)
    end = date.today()
    start = end - timedelta(days=days)

    try:
        df = ak.stock_zh_a_daily(
            symbol=sina_symbol,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
        )
    except Exception as e:
        raise ValueError(f"Failed to fetch bars for {stock_code}: {e}") from e

    if df.empty:
        raise ValueError(f"No bar data for {stock_code}")

    return df


def _score_consecutive_limits(count: int) -> int:
    if count >= 3:
        return 2
    if count == 2:
        return 1
    return 0


def _score_broken_seals(count: int) -> int:
    if count == 0:
        return 1
    return -1


def _score_seal_time(seal_time: str) -> int:
    if not seal_time or len(seal_time) < 4:
        return 0
    hour = int(seal_time[:2])
    minute = int(seal_time[2:4])
    total_minutes = hour * 60 + minute
    if total_minutes <= 9 * 60 + 35:
        return 1
    if total_minutes >= 10 * 60:
        return -1
    return 0


def _score_turnover(turnover: float) -> int:
    if turnover < 5:
        return 1
    if turnover > 15:
        return -1
    return 0


def _score_volume_trend(bars: pd.DataFrame) -> int:
    if len(bars) < 5:
        return 0
    recent_5 = bars.tail(5)["volume"].values
    avg_first = recent_5[:2].mean()
    avg_last = recent_5[-2:].mean()
    if avg_first == 0:
        return 0
    ratio = avg_last / avg_first
    if ratio > 1.5:
        return -1
    if ratio < 0.6:
        return 1
    return 0


def _score_price_trend(bars: pd.DataFrame) -> int:
    if len(bars) < 5:
        return 0
    close_5d_ago = float(bars.iloc[-5]["close"])
    close_now = float(bars.iloc[-1]["close"])
    if close_5d_ago == 0:
        return 0
    pct = (close_now - close_5d_ago) / close_5d_ago * 100
    if pct > 5:
        return -1
    if pct < -5:
        return 1
    return 0


def _score_to_predicted_change(score: int) -> float:
    if score >= 3:
        return 7.5
    if score >= 1:
        return 3.5
    if score >= -1:
        return 0.0
    return -3.5


def _analyze_stock(row: pd.Series, bars: pd.DataFrame, year_start_price: float) -> Prediction:
    """
    Analyze a single limit-up stock and predict tomorrow's change.

    Args:
        row: Row from stock_zt_pool_em DataFrame
        bars: Recent daily bars for this stock
        year_start_price: First close price of the year

    Returns:
        Prediction with all computed fields
    """
    code = str(row["代码"])
    price = float(row["最新价"])
    today_change = float(row["涨跌幅"])
    consecutive = int(row["连板数"])
    broken_seals = int(row["炸板次数"])
    seal_time = str(row["首次封板时间"])
    turnover = float(row["换手率"])
    industry = str(row["所属行业"])

    ytd_change = 0.0
    if year_start_price > 0:
        ytd_change = (price - year_start_price) / year_start_price * 100

    score = 0
    score += _score_consecutive_limits(consecutive)
    score += _score_broken_seals(broken_seals)
    score += _score_seal_time(seal_time)
    score += _score_turnover(turnover)
    score += _score_volume_trend(bars)
    score += _score_price_trend(bars)

    predicted = _score_to_predicted_change(score)

    return Prediction(
        code=code,
        name=str(row["名称"]),
        price=price,
        today_change=today_change,
        predicted_change=predicted,
        industry=industry,
        ytd_change=ytd_change,
        score=score,
    )


def scan_and_predict() -> List[Prediction]:
    """
    Scan today's limit-up stocks and predict tomorrow's movement.

    Returns:
        List of Prediction, sorted by predicted_change descending
    """
    today_str = date.today().strftime("%Y%m%d")

    try:
        zt_df = ak.stock_zt_pool_em(date=today_str)
    except Exception as e:
        raise ValueError(f"Failed to fetch limit-up pool for {today_str}: {e}") from e

    if zt_df.empty:
        return []

    predictions: List[Prediction] = []

    for _, row in zt_df.iterrows():
        code = str(row["代码"])
        try:
            bars = _get_recent_bars(code, 30)
        except ValueError:
            continue

        try:
            year_start_price = _get_year_start_price(code)
        except ValueError:
            year_start_price = 0.0

        pred = _analyze_stock(row, bars, year_start_price)
        predictions.append(pred)

    predictions.sort(key=lambda p: p.predicted_change, reverse=True)
    return predictions


def scan_and_predict_with_progress() -> Generator[Tuple[int, int, str, str], None, List[Prediction]]:
    """
    Scan today's limit-up stocks with progress reporting.

    Yields:
        (current_index, total_count, stock_code, stock_name) for each stock processed

    Returns:
        List of Prediction via StopIteration.value, sorted by predicted_change descending
    """
    today_str = date.today().strftime("%Y%m%d")

    try:
        zt_df = ak.stock_zt_pool_em(date=today_str)
    except Exception as e:
        raise ValueError(f"Failed to fetch limit-up pool for {today_str}: {e}") from e

    if zt_df.empty:
        return []

    total = len(zt_df)
    predictions: List[Prediction] = []

    for idx, (_, row) in enumerate(zt_df.iterrows()):
        code = str(row["代码"])
        name = str(row["名称"])
        yield idx + 1, total, code, name

        try:
            bars = _get_recent_bars(code, 30)
        except ValueError:
            continue

        try:
            year_start_price = _get_year_start_price(code)
        except ValueError:
            year_start_price = 0.0

        pred = _analyze_stock(row, bars, year_start_price)
        predictions.append(pred)

    predictions.sort(key=lambda p: p.predicted_change, reverse=True)
    return predictions


def main() -> None:
    """Scan limit-up stocks and print predictions."""
    print(f"Scanning limit-up stocks for {date.today()}...")
    predictions = scan_and_predict()

    if not predictions:
        print("No limit-up stocks found today.")
        return

    print(f"\nFound {len(predictions)} limit-up stocks:\n")
    print(
        f"{'代码':>8}  {'名称':<8}  {'最新价':>8}  {'今日涨幅':>8}  "
        f"{'明日预测':>8}  {'所属行业':<8}  {'年内涨幅':>8}  {'评分':>4}"
    )
    print("-" * 80)

    for p in predictions:
        print(
            f"{p.code:>8}  {p.name:<8}  {p.price:>8.2f}  {p.today_change:>+7.2f}%  "
            f"{p.predicted_change:>+7.1f}%  {p.industry:<8}  {p.ytd_change:>+7.1f}%  "
            f"{p.score:>+4d}"
        )


if __name__ == "__main__":
    main()