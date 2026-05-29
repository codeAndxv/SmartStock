"""Stock community links generator."""

import re
from dataclasses import dataclass
from typing import List
from urllib.parse import quote

import akshare as ak
import requests

from backend.core.stock_info import _to_market_prefix, _to_sina_symbol, get_stock_profile

_PREFIX_RE = re.compile(r"^(?:sh|sz|bj)?(\d{6})$", re.IGNORECASE)


def _strip_prefix(raw: str) -> str | None:
    """Strip market prefix from code. Returns bare 6-digit code or None."""
    m = _PREFIX_RE.match(raw.strip())
    return m.group(1) if m else None


def _fetch_name_via_sina(code: str) -> str:
    """Fetch stock name via Sina real-time quote API (fast, reliable)."""
    sina = _to_sina_symbol(code)
    url = f"https://hq.sinajs.cn/list={sina}"
    r = requests.get(url, headers={"Referer": "https://finance.sina.com.cn"}, timeout=5)
    r.raise_for_status()
    _, _, data = r.text.partition("=")
    fields = data.strip('";\n').split(",")
    if not fields or not fields[0]:
        raise ValueError(f"No data for {code}")
    return fields[0]


def _resolve_stock(code_or_name: str) -> tuple[str, str]:
    """Resolve input to (code, name).

    Args:
        code_or_name: Stock code, prefixed code, or name

    Returns:
        Tuple of (6-digit code, stock name)

    Raises:
        ValueError: If the input cannot be resolved
    """
    # Try stripping prefix first (e.g. "SZ000636" -> "000636")
    bare = _strip_prefix(code_or_name)

    if bare:
        # Input is a code — get name from Sina (fast, no timeout)
        try:
            name = _fetch_name_via_sina(bare)
            return bare, name
        except Exception:
            raise ValueError(f"Stock not found: {code_or_name}")

    # Input is a name — resolve to code via AKShare
    for _ in range(3):
        try:
            df = ak.stock_info_a_code_name()
            match = df[df["name"] == code_or_name]
            if match.empty:
                match = df[df["name"].str.contains(code_or_name, na=False)]
            if not match.empty:
                code = str(match.iloc[0]["code"]).zfill(6)
                name = str(match.iloc[0]["name"])
                return code, name
        except Exception:
            continue

    raise ValueError(f"Stock not found: {code_or_name}")


@dataclass
class StockLink:
    """A single link to a stock-related platform."""
    name: str
    url: str
    icon: str
    description: str


@dataclass
class StockLinksResult:
    """Result containing stock info and community links."""
    code: str
    name: str
    full_name: str
    links: List[StockLink]


def _build_links(code: str, search_name: str) -> List[StockLink]:
    """Build community links for a stock.

    Args:
        code: 6-digit stock code
        search_name: Name used for search-based links

    Returns:
        List of StockLink
    """
    xq_symbol = _to_market_prefix(code)
    sina_symbol = _to_sina_symbol(code)
    encoded_name = quote(search_name)

    return [
        StockLink(
            name="雪球",
            url=f"https://xueqiu.com/S/{xq_symbol}",
            icon="snowflake",
            description="投资者社区，实时讨论与观点分享",
        ),
        StockLink(
            name="东方财富股吧",
            url=f"https://guba.eastmoney.com/list,{code}.html",
            icon="chat",
            description="最活跃的A股散户讨论社区",
        ),
        StockLink(
            name="同花顺",
            url=f"https://stockpage.10jqka.com.cn/{code}/",
            icon="chart",
            description="行情数据、资金流向与技术分析",
        ),
        StockLink(
            name="新浪财经",
            url=f"https://finance.sina.com.cn/realstock/company/{sina_symbol}/nc.shtml",
            icon="news",
            description="新闻资讯与公司公告",
        ),
        StockLink(
            name="企查查",
            url=f"https://www.qcc.com/search?key={encoded_name}",
            icon="building",
            description="企业工商信息、股权穿透与关联公司",
        ),
        StockLink(
            name="爱企查",
            url=f"https://aiqicha.baidu.com/s?q={encoded_name}",
            icon="search",
            description="百度旗下企业信息查询平台",
        ),
        StockLink(
            name="巨潮资讯",
            url=f"http://www.cninfo.com.cn/new/fulltextSearch?notautosubmit=&keyWord={encoded_name}",
            icon="document",
            description="上市公司公告与年报披露",
        ),
    ]


def get_stock_links(code_or_name: str) -> StockLinksResult:
    """Get community links for a stock by code or name.

    Args:
        code_or_name: Stock code (e.g. "000001") or name (e.g. "平安银行")

    Returns:
        StockLinksResult with stock info and platform links

    Raises:
        ValueError: If the stock cannot be found
    """
    code, name = _resolve_stock(code_or_name)

    try:
        profile = get_stock_profile(code)
        full_name = profile.full_name
        display_name = profile.name
    except (ValueError, KeyError):
        full_name = name
        display_name = name

    links = _build_links(code, full_name)

    return StockLinksResult(
        code=code,
        name=display_name,
        full_name=full_name,
        links=links,
    )
