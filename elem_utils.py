import asyncio
from typing import Any

import nodriver as nd
from nodriver.cdp.runtime import ExceptionDetails, RemoteObject
import base64


async def wait_elem_and_click(tab: nd.Tab, xpath: str, timeout: float = 5.0) -> str | tuple[
    RemoteObject, ExceptionDetails | None] | Any:
    """
    通过 XPath 查找单个元素并点击（带重试和超时）。

    Args:
        tab:      nodriver 的 Tab 对象
        xpath:    XPath 表达式（用于定位单个元素）
        timeout:  超时时间（秒），默认 5 秒

    Raises:
        TimeoutError: 在指定时间内未能找到并点击元素
    """
    js_code = f"""
    (() => {{
        const result = document.evaluate(
            `{xpath}`,
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        );
        const element = result.singleNodeValue;
        if (!element) {{
            throw new Error(`XPath 未匹配到元素: {xpath}`);
        }}
        element.click();
        return true;
    }})()
    """

    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        try:
            return await tab.evaluate(js_code)
        except Exception:
            if asyncio.get_event_loop().time() >= deadline:
                raise TimeoutError(f"在 {timeout} 秒内未能通过 XPath 点击元素: {xpath}")
            await asyncio.sleep(0.1)


async def is_elem_exists(tab: nd.Tab, xpath: str) -> bool:
    """
    判断指定 XPath 的元素当前是否存在于 DOM 中（即时检查）。

    Args:
        tab:   nodriver 的 Tab 对象
        xpath: 元素的 XPath 表达式

    Returns:
        True 如果至少有一个匹配节点，否则 False
    """
    js_code = f"""
    (() => {{
        const result = document.evaluate(
            `{xpath}`,
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        );
        return result.singleNodeValue !== null;
    }})()
    """
    return await tab.evaluate(js_code)


async def wait_elem_exists(tab: nd.Tab, xpath: str, timeout: float = 5.0) -> bool:
    """
    等待指定 XPath 的元素出现（存在于 DOM 中）。

    Args:
        tab:      nodriver 的 Tab 对象
        xpath:    XPath 表达式
        timeout:  超时时间（秒），默认 5 秒

    Returns:
        在超时时间内元素出现则返回 True

    Raises:
        TimeoutError: 在指定时间内元素未出现
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        if await is_elem_exists(tab, xpath):
            return True
        if asyncio.get_event_loop().time() >= deadline:
            raise TimeoutError(f"在 {timeout} 秒内等待元素出现超时: {xpath}")
        await asyncio.sleep(0.1)


async def wait_for_page_ready(tab: nd.Tab, timeout: float = 10.0, stable_time: float = 0.5):
    """
    等待页面加载完成并且内容保持稳定。

    Args:
        tab:         nodriver 的 Tab 对象
        timeout:     最大等待时间（秒），默认 10 秒
        stable_time: 页面无变化视为稳定的持续时间（秒），默认 0.5 秒

    Raises:
        TimeoutError: 在指定时间内页面未能稳定加载
    """
    js_check_ready = """
    (() => {
        return document.readyState === 'complete';
    })()
    """
    js_get_dom_snapshot = """
    (() => {
        return document.body ? document.body.innerHTML.length : 0;
    })()
    """

    deadline = asyncio.get_event_loop().time() + timeout
    last_dom_length = -1
    stable_start = None

    while True:
        # 1. 检查 readyState 是否为 complete
        try:
            ready = await tab.evaluate(js_check_ready)
        except Exception:
            ready = False

        # 2. 获取当前 DOM 大小
        try:
            current_length = await tab.evaluate(js_get_dom_snapshot)
        except Exception:
            current_length = 0

        if ready and current_length > 0:
            if current_length == last_dom_length:
                # DOM 大小没有变化
                if stable_start is None:
                    stable_start = asyncio.get_event_loop().time()
                elif asyncio.get_event_loop().time() - stable_start >= stable_time:
                    return  # 页面稳定，退出
            else:
                # DOM 还在变化，重置稳定计时
                stable_start = None
            last_dom_length = current_length
        else:
            # 未就绪或无内容，重置稳定计时
            stable_start = None

        # 超时检查
        if asyncio.get_event_loop().time() >= deadline:
            raise TimeoutError(f"页面在 {timeout} 秒内未能稳定加载")

        await asyncio.sleep(0.2)


async def is_button_clickable(tab: nd.Tab, xpath: str) -> bool:
    """
    判断指定 XPath 的按钮当前是否处于可点击状态。

    Args:
        tab:   nodriver 的 Tab 对象
        xpath: 按钮的 XPath 表达式

    Returns:
        True 如果按钮当前可点击，否则 False
    """
    js_code = f"""
    (() => {{
        const result = document.evaluate(
            `{xpath}`,
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        );
        const elem = result.singleNodeValue;
        if (!elem) return false;
        if (elem.disabled) return false;
        if (!elem.offsetParent) return false;
        return true;
    }})()
    """
    return await tab.evaluate(js_code)


async def get_elem_text(tab: nd.Tab, xpath: str) -> str:
    """
    通过 XPath 获取单个元素的文本内容。

    Args:
        tab:   nodriver 的 Tab 对象
        xpath: 元素的 XPath 表达式

    Returns:
        元素的文本内容；如果元素不存在或获取失败，返回空字符串。
    """
    js_code = f"""
    (() => {{
        const result = document.evaluate(
            `{xpath}`,
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        );
        const element = result.singleNodeValue;
        if (!element) {{
            return '';
        }}
        return element.textContent || '';
    }})()
    """
    try:
        text = await tab.evaluate(js_code)
        return str(text) if text is not None else ''
    except Exception:
        return ''


async def wait_elem_text_equal_to(
        tab: nd.Tab, xpath: str, expected_text: str, timeout: float = 5.0
) -> bool:
    """
    等待指定 XPath 元素的文本内容与给定字符串相等。

    在超时时间内反复检查元素的 textContent 是否与 expected_text 严格相等。
    若相等则立即返回 True；若超时仍未相等，抛出 TimeoutError。

    Args:
        tab:           nodriver 的 Tab 对象
        xpath:         XPath 表达式
        expected_text: 期望的文本内容
        timeout:       超时时间（秒），默认 5 秒

    Returns:
        True（当文本相等时）

    Raises:
        TimeoutError: 在指定时间内文本未变为期望值
    """
    js_code = f"""
    (() => {{
        const result = document.evaluate(
            `{xpath}`,
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        );
        const el = result.singleNodeValue;
        return el ? (el.textContent || '') : null;
    }})()
    """

    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        try:
            text = await tab.evaluate(js_code)
        except Exception:
            text = None

        if text is not None and str(text) == expected_text:
            return True

        if asyncio.get_event_loop().time() >= deadline:
            raise TimeoutError(
                f"在 {timeout} 秒内等待元素文本等于 '{expected_text}' 超时 (XPath: {xpath})"
            )

        await asyncio.sleep(0.1)


async def wait_elem_text_exist_then_get(
        tab: nd.Tab, xpath: str, timeout: float = 5.0
) -> str:
    """
    等待指定 XPath 的元素出现并且其文本内容不为空，然后返回该文本。

    在超时时间内反复检查元素的 textContent，一旦元素存在且文本长度大于 0 即返回文本内容。
    若超时，则抛出 TimeoutError。

    Args:
        tab:     nodriver 的 Tab 对象
        xpath:   XPath 表达式
        timeout: 超时时间（秒），默认 5 秒

    Returns:
        元素存在且非空时的文本内容

    Raises:
        TimeoutError: 在指定时间内未能获取到文本
    """
    js_code = f"""
    (() => {{
        const result = document.evaluate(
            `{xpath}`,
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        );
        const el = result.singleNodeValue;
        if (!el) return null;
        const text = el.textContent || '';
        return text.length > 0 ? text : '';
    }})()
    """

    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        try:
            text = await tab.evaluate(js_code)
        except Exception:
            text = None

        if isinstance(text, str) and len(text) > 0:
            return text

        if asyncio.get_event_loop().time() >= deadline:
            raise TimeoutError(
                f"在 {timeout} 秒内等待元素文本出现超时: {xpath}"
            )

        await asyncio.sleep(0.1)


async def get_canvas_bytes(tab: nd.Tab, xpath: str) -> bytes:
    """
    获取指定 canvas 元素当前的 PNG 图像数据。

    Args:
        tab:   nodriver 的 Tab 对象
        xpath: canvas 元素的 XPath 表达式

    Returns:
        PNG 格式的字节数据

    Raises:
        ValueError: 未找到 canvas 元素或导出失败
    """
    js_code = f"""
    (() => {{
        const result = document.evaluate(
            `{xpath}`,
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        );
        const canvas = result.singleNodeValue;
        if (!canvas || canvas.tagName !== 'CANVAS') {{
            throw new Error('未找到 canvas 元素');
        }}
        return canvas.toDataURL('image/png');
    }})()
    """

    data_url = await tab.evaluate(js_code)

    if not isinstance(data_url, str) or not data_url.startswith('data:image/png;base64,'):
        raise ValueError('无效的 Canvas 数据 URL')

    # 去掉 data URL 前缀，解码 base64
    base64_str = data_url[len('data:image/png;base64,'):]
    return base64.b64decode(base64_str)


async def elem_scroll_into_view(tab: nd.Tab, xpath: str) -> bool:
    """
    将指定 XPath 的元素滚动到视图中（即时执行，不等待元素出现）。

    该函数直接执行一次查找，如果元素存在则调用其 scrollIntoView() 方法（无参数）。
    不会等待元素出现，也不会在元素缺失时抛出异常。

    Args:
        tab:   nodriver 的 Tab 对象
        xpath: 元素的 XPath 表达式

    Returns:
        如果元素存在且成功滚动则返回 True，否则返回 False。
    """
    js_code = f"""
    (() => {{
        const result = document.evaluate(
            `{xpath}`,
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        );
        const element = result.singleNodeValue;
        if (element) {{
            element.scrollIntoView();
            return true;
        }}
        return false;
    }})()
    """
    return await tab.evaluate(js_code)
