import asyncio
import json
import nodriver as nd


async def wait_for_page_ready(
        tab: nd.Tab,
        timeout: float = 10.0,
        stable_time: float = 0.5,
        interval: float = 0.5
):
    """
    等待页面加载完成并且内容保持稳定。

    Args:
        tab:         nodriver 的 Tab 对象
        timeout:     最大等待时间（秒），默认 10 秒
        stable_time: 页面无变化视为稳定的持续时间（秒），默认 0.5 秒
        interval:    检测轮询间隔（秒），默认 0.5 秒。
                     若大于 stable_time 会被自动调整为 stable_time，
                     以保证稳定判断的可靠性。

    Raises:
        TimeoutError: 在指定时间内页面未能稳定加载
    """
    # 冲突处理：检测间隔不能大于稳定时间，否则无法可靠判断稳定
    if interval > stable_time:
        interval = stable_time  # 静默调整，也可视需要在此添加警告日志

    js_check_ready = """
    (() => {
        return document.readyState === 'complete';
    })()
    """
    js_get_element_count = """
    (() => {
        return document.getElementsByTagName('*').length;
    })()
    """

    deadline = asyncio.get_event_loop().time() + timeout

    # 等待 readyState 变为 complete
    while True:
        try:
            ready = await tab.evaluate(js_check_ready)
        except Exception:
            ready = False
        if ready:
            break
        if asyncio.get_event_loop().time() >= deadline:
            raise TimeoutError(f"页面在 {timeout} 秒内未能稳定加载")
        await asyncio.sleep(interval)

    # 等待元素数量稳定
    last_count = -1
    stable_start = None

    while True:
        try:
            current_count = await tab.evaluate(js_get_element_count)
        except Exception:
            current_count = 0
        if current_count > 0:
            if current_count == last_count:
                if stable_start is None:
                    stable_start = asyncio.get_event_loop().time()
                elif asyncio.get_event_loop().time() - stable_start >= stable_time:
                    return  # 稳定达成
            else:
                stable_start = None
            last_count = current_count
        else:
            stable_start = None

        if asyncio.get_event_loop().time() >= deadline:
            raise TimeoutError(f"页面在 {timeout} 秒内未能稳定加载")
        await asyncio.sleep(interval)


async def simple_http_get(tab: nd.Tab, url: str, timeout: float = 5.0) -> dict:
    """
    使用简单的 HTTP GET 请求获取 JSON 响应并解析为字典。 假定接口总是返回 JSON，否则将抛出错误。

    Args:
        tab:     nodriver 的 Tab 对象
        url:     请求 URL（支持相对路径，如 "/api/data"）
        timeout: 超时时间（秒），默认 5 秒

    Returns:
        解析后的 Python 字典

    Raises:
        ValueError: 网络错误、超时、非 2xx 状态码或响应不是有效 JSON
    """

    js_code = f"""
        fetch({json.dumps(url)})
            .then(response => {{
                if (!response.ok) {{
                    throw new Error('HTTP ' + response.status);
                }}
                return response.text();
            }})
    """

    try:
        raw_text = await asyncio.wait_for(
            tab.evaluate(js_code, await_promise=True),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise ValueError(f"请求超时 ({timeout}s): {url}")
    except Exception as e:
        raise ValueError(f"请求失败: {url} - {e}")

    # 将文本解析为 JSON
    try:
        result = json.loads(str(raw_text))
    except json.JSONDecodeError as e:
        raise ValueError(f"响应不是有效的 JSON: {url} - {e}")

    if not isinstance(result, dict):
        raise ValueError(f"响应 JSON 不是字典对象: {url}")

    return result
