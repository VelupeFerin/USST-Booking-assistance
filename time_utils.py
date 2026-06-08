import time
import datetime
import asyncio


def get_current_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # return time.time()


def time_slot_number_to_time_slot_text(time_slot_number):
    t_int = int(time_slot_number)
    return f'{t_int + 8}:00-{t_int + 9}:00'


async def async_waiting_until(h: int, m: int, s: int) -> None:
    """
    异步等待至今天的 h:m:s 时刻（24小时制）。
    若当前时间已过该时刻，则等待至明天的同一时刻。
    若 s < 0，则直接返回，不等待。
    精度为秒，能够适应系统休眠/唤醒以及系统时间调整。
    """
    if s < 0:
        return

    # 获取当前本地时间，并构建目标时间（微秒置零）
    now = datetime.datetime.now()
    target = now.replace(hour=h, minute=m, second=s, microsecond=0)

    # 如果目标时间已过，推迟到明天
    if target <= now:
        target += datetime.timedelta(days=1)

    # 转换为 Unix 时间戳（与 time.time() 保持一致）
    target_ts = target.timestamp()

    # 循环等待，每次最多休眠 1 秒，以便及时响应系统唤醒或时间跳变
    while True:
        remaining = target_ts - time.time()
        if remaining <= 0:
            break
        # 休眠剩余时间，但每次不超过 1 秒
        await asyncio.sleep(min(remaining, 1))
