import asyncio
import os
from collections import defaultdict
import nodriver as nd

from PageObject import BasePageObject, UserInfoPageObject
from time_utils import get_current_time


def check_booking_tasks():
    """
    从同目录下的 "BookingTaskList.txt" 读取预订任务，按规则检查。
    如果检查通过，返回空字符串；
    如果不通过，返回错误原因及涉及的任务（包含行号和原始内容）。
    """

    with open("BookingTaskList.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

    errors = []
    valid_tasks = []  # 存储解析正确的任务信息，用于后续规则检查
    # valid_tasks 中每个元素: (行号, 原始行内容, 人, 场馆, 时间号, 场地号)

    # ---------- 第一遍：逐行解析与基本格式检查 ----------
    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:  # 跳过空行
            continue

        parts = line.split()
        if len(parts) != 4:
            errors.append(f"格式错误 (字段数不为4): 第{idx}行 '{raw_line.strip()}'")
            continue

        person, venue_str, time_str, court_str = parts

        # 场馆必须为 516 或 1100
        if venue_str not in ("516", "1100"):
            errors.append(f"场馆无效 (只能为516或1100): 第{idx}行 '{raw_line.strip()}'")
            continue

        # 时间号与场地号必须为整数
        try:
            time_num = int(time_str)
            court_num = int(court_str)
        except ValueError:
            errors.append(f"时间号或场地号不是有效整数: 第{idx}行 '{raw_line.strip()}'")
            continue

        # 时间号范围 1~12
        if not (1 <= time_num <= 12):
            errors.append(f"时间号超出范围 (1~12): 第{idx}行 '{raw_line.strip()}'")
            continue

        # 场地号范围
        if venue_str == "516":
            if not (1 <= court_num <= 19):
                errors.append(f"516场馆场地号超出范围 (1~19): 第{idx}行 '{raw_line.strip()}'")
                continue
        else:  # 1100
            if not (1 <= court_num <= 8):
                errors.append(f"1100场馆场地号超出范围 (1~8): 第{idx}行 '{raw_line.strip()}'")
                continue

        # 格式完全正确，记录下来
        valid_tasks.append((idx, raw_line.strip(), person, venue_str, time_num, court_num))

    # ---------- 第二遍：业务规则检查 ----------
    # 规则4：同一个人不能在同一场馆预订两个场次
    person_venue_map = defaultdict(list)  # key: (人, 场馆) -> list of (行号, 原始行)
    for task in valid_tasks:
        idx, raw, person, venue, t, c = task
        person_venue_map[(person, venue)].append((idx, raw))

    for (person, venue), task_list in person_venue_map.items():
        if len(task_list) > 1:
            lines_info = ", ".join(f"第{idx}行 '{raw}'" for idx, raw in task_list)
            errors.append(
                f"同一人同一场馆重复预订: {person} 在 {venue} 场馆预订了 {len(task_list)} 个场次 -> {lines_info}")

    # 规则5：同一场馆的同一场次（时间号+场地号）不能被超过两人预订
    venue_slot_map = defaultdict(list)  # key: (场馆, 时间号, 场地号) -> list of (人, 行号, 原始行)
    for task in valid_tasks:
        idx, raw, person, venue, t, c = task
        venue_slot_map[(venue, t, c)].append((person, idx, raw))

    for (venue, t, c), bookings in venue_slot_map.items():
        if len(bookings) > 2:
            people_info = ", ".join(f"{person}(第{idx}行)" for person, idx, _ in bookings)
            errors.append(
                f"同一场次超过2人预订: {venue}场馆 时间号{t} 场地号{c} 被 {len(bookings)} 人预订 -> {people_info}"
            )

    if errors:
        return f"[{get_current_time()}] 任务检查未通过，发现以下错误:\n" + "\n".join(
            f"{i + 1}. {err}" for i, err in enumerate(errors))
    else:
        return ""


async def check_cookies():
    c_set = set()
    with open("BookingTaskList.txt", "r") as fc:
        for tp in fc.readlines():
            c_set.add(tp.split()[0])
    check_cookies_tasks = []
    err_msg_list = []
    x_i = 0
    for x in c_set:
        check_cookies_tasks.append(check_person_cookies_by_browser(x, x_i, err_msg_list))
        x_i += 1
    results = await asyncio.gather(*check_cookies_tasks)
    if all(results):
        return True
    else:
        print(f"[{get_current_time()}] Cookies检查未通过，发现以下错误：")
        for err in err_msg_list:
            print(err)
        return False


async def check_person_cookies_by_browser(c, c_i, err_msg_list):
    if not os.path.exists(f'Cookies/{c}.cookies'):
        err_msg_list.append(f'缺少{c}.cookies，请补充')
        return False

    browser = await nd.start(browser_args=[f"--window-position={32 * c_i},{32 * c_i}"])
    bp = BasePageObject(browser)
    try:
        await browser.cookies.load(f"Cookies/{c}.cookies")
    except Exception:
        err_msg_list.append(f'{c}.cookies 无效')
        browser.stop()
        return False

    uip = await bp.get_my_info_page()
    i = 20
    while i > 0:
        username = await uip.get_username()
        if username == '--' or username == '':
            await asyncio.sleep(0.5)
            i -= 1
        else:
            browser.stop()
            return True
    else:
        err_msg_list.append(f'{c}.cookies 无效')
        browser.stop()
        return False


def get_booking_task():
    rts = []
    with open("BookingTaskList.txt", "r") as btl:
        tasks = btl.readlines()
        task_amount = len(tasks)
        for task in tasks:
            task_info = task.split()
            rts.append({
                "person": task_info[0],
                "venue": task_info[1],
                "time_slot_number": task_info[2],
                "field": task_info[3],
                "task_amount": task_amount
            })
    return rts
