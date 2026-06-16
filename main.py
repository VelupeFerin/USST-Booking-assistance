import asyncio
import os
import sys

import aiofiles
import nodriver as nd

import PageObject
from task_utils import get_booking_task, check_booking_tasks, check_cookies
from time_utils import async_waiting_until, get_current_time, time_slot_number_to_time_slot_text


def init_dir_and_files():
    os.makedirs('QRcode', exist_ok=True)
    os.makedirs('Cookies', exist_ok=True)
    os.makedirs('session_snapshot', exist_ok=True)
    if not os.path.exists('BookingTaskList.txt'):
        with open('BookingTaskList.txt', 'w', encoding='utf-8') as f:
            pass


async def booking_task_execute(task, browser):
    person = task["person"]
    time_slot_number = task["time_slot_number"]
    time_slot_text = time_slot_number_to_time_slot_text(time_slot_number)
    field = task["field"]
    venue = task["venue"]

    print(f'[{get_current_time()}] {person} {venue} 启动浏览器')
    await browser.cookies.load(f"Cookies/{person}.cookies")
    bp = PageObject.BasePageObject(browser.main_tab)
    bsp = await bp.get_venue_page(venue)

    await bsp.wait_for_page_ready()
    await bsp.click_date()
    print(f'[{get_current_time()}] {person} {venue} 正在等待直到6:59:57')
    # await asyncio.sleep(3)
    # await async_waiting_until(3, 7, 0)
    await async_waiting_until(6, 59, 57)
    print(f'[{get_current_time()}] {person} {venue} 开始订场')
    if not await bsp.waiting_session_open_and_select(time_slot_number, field):
        print(f'[{get_current_time()}] {person} {venue} 场次不可选')
        session_snapshot_bytes = await bsp.get_session_snapshot_bytes(time_slot_number, field)
        session_snapshot_file_name = f'[{get_current_time()}] {person} {venue} {time_slot_text} {task["field"]}号场.png'.replace(
            ':', '：')
        with open(os.path.join('session_snapshot', session_snapshot_file_name), "wb") as fss:
            fss.write(session_snapshot_bytes)
        print(
            f'[{get_current_time()}] {person} {venue} 场次不可选时的场次快照已保存到session_snapshot/{session_snapshot_file_name}')
        browser.stop()
        return
    snp = await bsp.confirm_box_click()
    print(f'[{get_current_time()}] {person} {venue} 已选择场次')

    if not await snp.click_add_session_number():
        print(f'[{get_current_time()}] {person} {venue} 场次库存不足')
        browser.stop()
        return
    print(f'[{get_current_time()}] {person} {venue} 确认场次和数量')
    prp = await snp.click_next_step_button(retry=10 + 5 * task["task_amount"])
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


async def main():
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

    print(f'[{get_current_time()}] 正在等待直到6:59:00')
    await async_waiting_until(6, 59, 0)
    tasks = []
    i = 0
    for t in tasks_paras:
        browser = await nd.start(browser_args=["--window-size=1280,720", f"--window-position={32 * i},{32 * i}"])
        tasks.append(asyncio.create_task(booking_task_execute(t, browser)))
        i += 1
    for done in asyncio.as_completed(tasks):
        try:
            await done
        except Exception as e:
            print(f"{e}")


if __name__ == '__main__':
    os.chdir(os.path.dirname(sys.executable))
    init_dir_and_files()
    nd.loop().run_until_complete(main())
    input()
