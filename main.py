import asyncio
import datetime
import os
import sys
import aiofiles
import nodriver as nd
import PageObject
from datetime import datetime, time
from task_utils import get_booking_task, check_booking_tasks, check_cookies
from time_utils import async_waiting_until, get_current_time, time_slot_number_to_time_slot_text


def init_dir_and_files():
    os.makedirs('QRcode', exist_ok=True)
    os.makedirs('Cookies', exist_ok=True)
    os.makedirs('session_snapshot', exist_ok=True)
    if not os.path.exists('BookingTaskList.txt'):
        with open('BookingTaskList.txt', 'w', encoding='utf-8'):
            pass


async def booking_task_execute(task, browser, paras):
    person = task["person"]
    venue = task["venue"]
    time_slot_number = task["time_slot_number"]
    field = task["field"]
    target_sessions = {(int(time_slot_number), int(field))}  # TODO:此处暂时使用集合，便于为后继单个任务订多个场次的改动
    stock = task["stock"]
    target_date_offset = paras["target_date_offset"]
    now_exec = paras["now_exec"]

    print(f'[{get_current_time()}] {person} {venue} 启动浏览器')
    await browser.cookies.load(f"Cookies/{person}.cookies")
    bp = PageObject.BasePageObject(browser.main_tab)
    bsp = await bp.get_venue_page(venue)

    await bsp.set_target_date_offset(target_date_offset)
    await bsp.wait_for_page_ready()
    await bsp.set_server_time_duration(3600)
    selected_sessions = await bsp.select_sessions(target_sessions)
    for s in target_sessions - selected_sessions:
        time_slot_text = time_slot_number_to_time_slot_text(s[0])
        session_snapshot_file_name = f'[{get_current_time()}] {person} {venue} {time_slot_text} {task["field"]}号场.png'.replace(
            ':', '：')
        session_snapshot_bytes = await bsp.get_session_snapshot_bytes(s[0], s[1])
        async with aiofiles.open(os.path.join('session_snapshot', session_snapshot_file_name), "wb") as fss:
            await fss.write(session_snapshot_bytes)
        print(
            f'[{get_current_time()}] {person} {venue} 存在场次不可选，快照已保存到session_snapshot/{session_snapshot_file_name}')
    if not await bsp.click_next_step_button():
        print(f'[{get_current_time()}] {person} {venue} 此任务的所有场次都不可选')
        browser.stop()
        return
    print(f'[{get_current_time()}] {person} {venue} 已选择场次')

    if not now_exec:
        print(f'[{get_current_time()}] {person} {venue} 正在等待直到07:00:00')
        await bsp.waiting_server_time_until(datetime.combine(datetime.today(), time(7, 0, 0)))
    snp = await bsp.confirm_box_click()
    print(f'[{get_current_time()}] {person} {venue} 已确认场次')
    if not await snp.set_session_number(stock):
        print(f'[{get_current_time()}] {person} {venue} 场次库存不足')
        browser.stop()
        return
    print(f'[{get_current_time()}] {person} {venue} 确认场次和数量')
    prp = await snp.click_next_step_button(timeout=10 + 5 * task["task_amount"])
    if prp is None:
        print(f'[{get_current_time()}] {person} {venue} 场次预订失败（在数量选择页）')
        browser.stop()
        return
    print(f'[{get_current_time()}] {person} {venue} 场次预订成功')

    odp = await prp.get_order_detail_page_by_url()
    await odp.wait_for_page_ready()
    order_id = await odp.get_order_id()
    order_info = (await odp.get_order_info()).replace(':', '：')
    order_date = order_info[0:10]
    qrcode_bytes = await odp.get_qrcode_bytes()
    folder_path = os.path.join('QRcode', f'{order_date}')
    os.makedirs(folder_path, exist_ok=True)
    async with aiofiles.open(os.path.join(folder_path, f"{person} {venue} {order_info}{order_id}.png"), "wb") as f:
        await f.write(qrcode_bytes)
    print(f'[{get_current_time()}] {person} {venue} 订单二维码已导出')

    browser.stop()
    return


async def open_homepage():
    cookies_mapping = {}
    try:
        i = 1
        for filename in os.listdir('Cookies'):
            if os.path.isfile(os.path.join('Cookies', filename)) and filename.endswith(".cookies"):
                cookies_mapping[i] = filename[0:-8]
                i += 1
    except FileNotFoundError:
        pass

    if len(cookies_mapping) == 0:
        input("当前Cookies文件夹内没有cookies")
        return
    else:
        print("以下为当前cookies:")
        for k, v in cookies_mapping.items():
            print(f"{k}: {v}")
    persons_number = input("请输入多个要用于打开主页的cookies序号，用空格分隔：")
    i = 0
    for p_n in persons_number.split():
        try:
            p = cookies_mapping[int(p_n)]
        except (KeyError, ValueError):
            print(f"格式错误或没有此序号的cookies:{p_n}")
            continue
        if not os.path.exists(f'Cookies/{p}.cookies'):
            print(f'{p}.cookies 不存在')
            continue
        browser = await nd.start(browser_args=[f"--window-position={100 * i},0"])
        await browser.cookies.load(f"Cookies/{p}.cookies")
        await browser.get('https://usst.ydmap.cn/user/my')
        i += 1


async def main(paras):
    print(f'[{get_current_time()}] 进行前置检查')

    with open("BookingTaskList.txt", "r", encoding='utf-8') as fb:
        if len(fb.readlines()) == 0:
            print(f'[{get_current_time()}] 没有任务需要执行')
            return

    try:
        browser = await nd.start()
    except Exception as e:
        print(f'[{get_current_time()}] 浏览器启动异常：{e}')
        return
    browser.stop()

    cbrt = check_booking_tasks()
    if not cbrt == "":
        print(cbrt)
        return

    if not await check_cookies():
        return

    print(f'[{get_current_time()}] 前置检查无错误')

    tasks_paras = get_booking_task()
    print(f'[{get_current_time()}] 将要执行以下任务：')
    for t in tasks_paras:
        time_slot_text = time_slot_number_to_time_slot_text(t["time_slot_number"])
        session_text = f'{time_slot_text} {t["field"]}号场'
        print(f'{t["person"]} 订 {t["venue"]}校区 {session_text}')

    if paras.get("now_exec"):
        input("点击Enter确认并开始执行")
    else:
        print(f'[{get_current_time()}] 正在等待直到06:59:00')
        await async_waiting_until(6, 59, 0)
    tasks = []
    i = 0
    for t in tasks_paras:
        browser = await nd.start(browser_args=["--window-size=1280,720", f"--window-position={32 * i},{32 * i}"])
        tasks.append(asyncio.create_task(booking_task_execute(t, browser, paras)))
        i += 1
    for done in asyncio.as_completed(tasks):
        try:
            await done
        except Exception as e:
            print(f"{e}")


if __name__ == '__main__':
    os.chdir(os.path.dirname(sys.executable)) # 调试时需要注释掉此行
    init_dir_and_files()
    c = input(
        "1：明天7:00订场\n2：立即订今天的场\n3：立即订明天的场（需要明天的场已开放预订）\n4、使用cookies打开主页\n请输入选项：")
    if c in ["1", "2", "3", "4"]:
        if c == "4":
            nd.loop().run_until_complete(open_homepage())
        else:
            paras = {"now_exec": False if c == "1" else True, "target_date_offset": 0 if c == "2" else 1}
            nd.loop().run_until_complete(main(paras))
    input()
