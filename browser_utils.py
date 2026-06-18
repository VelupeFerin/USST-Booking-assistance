import asyncio
import json
import nodriver as nd


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
