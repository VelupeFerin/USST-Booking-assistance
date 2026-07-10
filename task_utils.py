import asyncio
import json
import os
from datetime import datetime, time, timedelta
from collections import defaultdict
import nodriver as nd
from PageObject import BasePageObject
from time_utils import get_current_time

# ==================== 场馆配置字典 ====================

VENUE_CONFIG = {
    "516": {
        "open_time": time(7, 0),  # 开放预订时间 7:00
        "max_tickets_per_slot": 4,  # 每个场次最大票数
        "max_tickets_per_person_per_slot": 2,  # 每人每场次最大可订票数
        "max_orders_per_person": 1,  # 每人最大订单数
        "max_slots_per_order": 1,  # 每个订单最大场次数
        "time_slots": ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', '13:00-14:00', '14:00-15:00',
                       '15:00-16:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
        "courts": [f"{i}号羽毛球场" for i in range(1, 20)]  # 场地号 0~18
    },
    "1100": {
        "open_time": time(7, 0),
        "max_tickets_per_slot": 4,
        "max_tickets_per_person_per_slot": 2,
        "max_orders_per_person": 1,
        "max_slots_per_order": 1,
        "time_slots": ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', '13:00-14:00', '14:00-15:00',
                       '15:00-16:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
        "courts": [f"{i}号羽毛球场" for i in range(1, 9)]  # 场地号 0~7
    },
    "516t": {
        "open_time": time(9, 0),
        "max_tickets_per_slot": 4,
        "max_tickets_per_person_per_slot": 4,
        "max_orders_per_person": 1,
        "max_slots_per_order": 4,
        "time_slots": ['09:00-09:30', '09:30-10:00', '10:00-10:30', '10:30-11:00', '11:00-11:30', '11:30-12:00',
                       '12:00-12:30', '12:30-13:00', '13:00-13:30', '13:30-14:00', '14:00-14:30', '14:30-15:00',
                       '15:00-15:30', '15:30-16:00', '16:00-16:30', '16:30-17:00', '17:00-17:30', '17:30-18:00',
                       '18:00-18:30', '18:30-19:00', '19:00-19:30', '19:30-20:00', '20:00-20:30', '20:30-21:00'],
        "courts": [f"{i}号网球场" for i in range(1, 4)]  # 场地号 0~2
    }
}


# ==================== 检查函数 ====================
def load_and_check_booking_tasks():
    """
    读取同目录下的 BookingTasks.json 并进行规则检查。
    检查通过：返回转换后的任务组字典列表（内部表示）。
    检查失败：返回包含错误原因的字符串。
    """

    try:
        with open("BookingTasks.json", "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        return f"错误: JSON 解析失败 - {e}"

    if not isinstance(raw_data, list):
        return "错误: JSON 顶层结构必须是数组。"

    errors = []
    # 用于存储转换后的任务组列表
    task_groups = []

    # ---------- 逐任务组检查与转换 ----------
    for group_idx, group in enumerate(raw_data, start=1):
        # 基本结构校验
        if not isinstance(group, dict):
            errors.append(f"任务组 {group_idx}: 格式错误，不是有效对象。")
            continue
        venue_name = group.get("venue")
        date_str = group.get("date")
        immediate = group.get("immediate")  # 期望布尔值
        tasks_raw = group.get("tasks")

        # 检查必需字段存在性
        if venue_name is None or date_str is None or immediate is None or tasks_raw is None:
            errors.append(f"任务组 {group_idx}: 缺少必要字段 (venue/date/immediate/tasks)。")
            continue
        if not isinstance(tasks_raw, list):
            errors.append(f"任务组 {group_idx}: 'tasks' 必须为数组。")
            continue

        # 检查场馆名有效性
        if venue_name not in VENUE_CONFIG:
            errors.append(f"任务组 {group_idx}: 无效场馆名 '{venue_name}'。")
            continue
        config = VENUE_CONFIG[venue_name]

        # 解析日期
        try:
            task_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            errors.append(f"任务组 {group_idx}: 日期格式错误，需为 'YYYY-MM-DD'。")
            continue

        # 初始化任务组字典
        group_dict = {
            "venue_name": venue_name,
            "date": task_date,
            "immediate": immediate,
            "booking_start_time": None,  # 稍后填充
            "venue_open_time": None,  # 稍后填充
            "tasks": []
        }

        # 如果非立即执行，计算开放时间和预订开始时间
        if not immediate:
            open_time = config["open_time"]
            venue_open_datetime = datetime.combine(task_date, open_time)
            booking_start = venue_open_datetime - timedelta(minutes=1)
            group_dict["venue_open_time"] = venue_open_datetime
            group_dict["booking_start_time"] = booking_start

        # 遍历任务列表进行转换和规则检查
        person_order_count = defaultdict(int)  # 统计每人订单数 (任务数)

        for task_idx, task in enumerate(tasks_raw, start=1):
            if not isinstance(task, dict):
                errors.append(f"任务组 {group_idx}, 任务 {task_idx}: 格式错误。")
                continue
            person = task.get("person")
            slots_raw = task.get("slots")
            if person is None or slots_raw is None:
                errors.append(f"任务组 {group_idx}, 任务 {task_idx}: 缺少 'person' 或 'slots'。")
                continue
            if not isinstance(slots_raw, list):
                errors.append(f"任务组 {group_idx}, 任务 {task_idx}: 'slots' 必须为数组。")
                continue

            # 检查订单内场次数是否超过限制
            if len(slots_raw) > config["max_slots_per_order"]:
                errors.append(
                    f"任务组 {group_idx}, 任务 {task_idx} ({person}): "
                    f"场次数 {len(slots_raw)} 超过上限 {config['max_slots_per_order']}。"
                )
            # 转换场次列表
            converted_slots = []
            for slot_idx, slot in enumerate(slots_raw, start=1):
                if not isinstance(slot, dict):
                    errors.append(f"任务组 {group_idx}, 任务 {task_idx}, 场次 {slot_idx}: 格式错误。")
                    continue
                time_str = slot.get("time")
                court_name = slot.get("court")
                tickets = slot.get("tickets")
                if time_str is None or court_name is None or tickets is None:
                    errors.append(
                        f"任务组 {group_idx}, 任务 {task_idx}, 场次 {slot_idx}: "
                        "缺少 'time', 'court' 或 'tickets'。"
                    )
                    continue

                # 时间段合法性及时间号转换
                time_slots = config["time_slots"]
                if time_str not in time_slots:
                    errors.append(
                        f"任务组 {group_idx}, 任务 {task_idx}, 场次 {slot_idx}: "
                        f"无效时间段 '{time_str}'（场馆 {venue_name}）。"
                    )
                    continue
                time_slot_num = time_slots.index(time_str)

                # 场地名合法性及场地号转换
                courts = config["courts"]
                if court_name not in courts:
                    errors.append(
                        f"任务组 {group_idx}, 任务 {task_idx}, 场次 {slot_idx}: "
                        f"无效场地名 '{court_name}'（场馆 {venue_name}）。"
                    )
                    continue
                court_num = courts.index(court_name)

                # 票数合法性（整数检查）
                if not isinstance(tickets, int) or tickets <= 0:
                    errors.append(
                        f"任务组 {group_idx}, 任务 {task_idx}, 场次 {slot_idx}: "
                        f"票数必须为正整数，实际为 {tickets}。"
                    )
                    continue

                # 每人每场次最大票数
                if tickets > config["max_tickets_per_person_per_slot"]:
                    errors.append(
                        f"任务组 {group_idx}, 任务 {task_idx}, 场次 {slot_idx} "
                        f"({person}): 订票数 {tickets} 超过每人每场次上限 "
                        f"{config['max_tickets_per_person_per_slot']}。"
                    )

                converted_slots.append({
                    "time_slot": time_slot_num,
                    "court": court_num,
                    "tickets": tickets
                })

            # 记录该任务（订单）到任务组
            group_dict["tasks"].append({
                "person": person,
                "slots": converted_slots
            })
            person_order_count[person] += 1

        # 检查每人订单数上限
        for person, count in person_order_count.items():
            if count > config["max_orders_per_person"]:
                errors.append(
                    f"任务组 {group_idx}: {person} 的订单数 {count} 超过上限 "
                    f"{config['max_orders_per_person']}。"
                )

        # 汇总同一任务组内每个场次的票数总和，检查场次总票数上限
        slot_tickets_sum = defaultdict(int)  # key: (time_slot, court)
        for task in group_dict["tasks"]:
            for slot in task["slots"]:
                key = (slot["time_slot"], slot["court"])
                slot_tickets_sum[key] += slot["tickets"]

        for (ts, court), total in slot_tickets_sum.items():
            if total > config["max_tickets_per_slot"]:
                time_str = config["time_slots"][ts]
                court_str = config["courts"][court]
                errors.append(
                    f"任务组 {group_idx}: 场次 ({time_str}, {court_str}) 总票数 {total} "
                    f"超过上限 {config['max_tickets_per_slot']}。"
                )

        task_groups.append(group_dict)

    if errors:
        return "检查未通过，发现以下错误:\n" + "\n".join(
            f"{i + 1}. {err}" for i, err in enumerate(errors)
        )
    else:
        return task_groups


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


async def check_cookies_new():
    try:
        with open("BookingTasks.json", "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            c_set = set()
            for task_group in raw_data:
                for task in task_group["tasks"]:
                    c_set.add(task["person"])
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
    except json.JSONDecodeError:
        return False


async def check_cookies():
    c_set = set()
    with open("BookingTaskList.txt", "r", encoding='utf-8') as fc:
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
    bp = BasePageObject(browser.main_tab)
    try:
        await browser.cookies.load(f"Cookies/{c}.cookies")
    except Exception:
        err_msg_list.append(f'{c}.cookies 无效')
        browser.stop()
        return False

    uip = await bp.get_my_info_page()
    username = await uip.wait_username_then_get()
    browser.stop()
    if username == c:
        return True
    else:
        err_msg_list.append(f'{c}.cookies 无效，或检查过程中出现错误')
        return False


# TODO：新的读取逻辑完成了，接下来需要整合到代码中（已经完成load_and_check_booking_tasks和check_cookies_new）
# ==================== 示例用法 ====================
async def mainabc():
    result = load_and_check_booking_tasks()
    if isinstance(result, list):
        print("检查通过，任务组列表：")
        print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
    else:
        print(result)
    rs = await check_cookies_new()
    print(rs)


if __name__ == "__main__000":
    nd.loop().run_until_complete(mainabc())


def get_booking_task():
    rts = []
    with open("BookingTaskList.txt", "r", encoding='utf-8') as btl:
        tasks = btl.readlines()
        task_amount = len(tasks)
        for task in tasks:
            task_info = task.split()
            rts.append({
                "person": task_info[0],
                "venue": task_info[1],
                "time_slot_number": task_info[2],
                "field": task_info[3],
                "task_amount": task_amount,
                "stock": 2
            })
    return rts
