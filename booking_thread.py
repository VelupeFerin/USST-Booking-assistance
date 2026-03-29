import base64
from io import BytesIO

import selenium.common
from PIL import Image
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from undetected_chromedriver import Chrome

from Config import booking_time, time_out, check_frequency
from funct import *

# 校区和网站链接
CL = {"516": "https://usst.ydmap.cn/booking/schedule/102285?salesItemId=102831",
      "1100": "https://usst.ydmap.cn/booking/schedule/102293?salesItemId=102829"}


def send_cookie(driver, person):
    with open(f'./CookieList/{person}.txt', 'r') as f:
        cookies_text = f.read()
    for cookie in cookies_text.split('; '):
        name, value = cookie.split('=', 1)
        cookie_dict = {
            'name': name,
            'value': value,
            'domain': '.ydmap.cn',
            'path': '/'
        }
        if "Hm_lpvt_" in name:
            cookie_dict['value'] = str(int(time.time()))
        if "YdmapKey" in name:
            cookie_dict['domain'] = 'usst.ydmap.cn'
        try:
            driver.add_cookie(cookie_dict)
        except Exception as e:
            print(f"[{get_current_time()}] {person}: Cookie {name} 添加失败: {e}")
    print(f"[{get_current_time()}] {person}: Cookie已添加")


def init_driver(order):
    # 使用本地缓存的驱动
    driver = Chrome(driver_executable_path='chromedriver/undetected_chromedriver.exe')
    order["semaphore"]["activate_num"] += 1
    # 让窗口之间至少有一部分露出，否则有些操作无法完成
    driver.set_window_rect(x=32 * order["task_sequence"], y=32 * order["task_sequence"])
    driver.get('https://usst.ydmap.cn/')
    # 需要先进入网站再发送cookie,不同浏览器的cookie不兼容
    send_cookie(driver, order["person"])
    time.sleep(1)  # 可能出现cookie未及时被处理而进入网站，导致需要登录的情况
    driver.get('https://usst.ydmap.cn/user/my')
    return driver


def save_qrcode(driver, person):
    driver.get(f"https://usst.ydmap.cn/order/{driver.current_url[26:-6]}")  # 订场成功后跳转的网址中包含了订单号，可以直达
    driver.implicitly_wait(time_out)
    tmp_ele = driver.find_element(By.XPATH, '/html/body/div[2]/div/div/div/div[1]/div[2]/div[1]/section[1]/div[1]/div/div')
    venue_info = tmp_ele.find_element(By.XPATH, './div[1]/div[2]/div[1]/div[2]/div[2]/div[1]').text
    canvas_base64 = driver.execute_script("return arguments[0].toDataURL('image/png').substring(21);",
                                          tmp_ele.find_element(By.XPATH,
                                                               "./div[4]/div[2]/div/div/div/div/div[2]/div/div[1]/div/div/div[2]/div[2]/div/canvas"
                                                               ))
    driver.quit()
    image = Image.open(BytesIO(base64.b64decode(canvas_base64)))
    image.save(f"./VenueQRcode/{person} - {venue_info.replace(':', '：')}.png")  # 把英文冒号换成中文冒号
    print(f"[{get_current_time()}] {person}: 二维码已保存")


def booking_venue(driver, order, venue):
    access_restriction = False
    while True:
        # 定位到单元格，检查是否可约，tr[时间]，td[场地]
        check_venue = WebDriverWait(driver, time_out, check_frequency).until(
            ec.presence_of_element_located((By.XPATH,
                                            f'//*[@id="app"]/div/div/section/div[1]/div[3]/div/div[3]/table/tbody/tr[{int(order["time_slot"][0:2]) - 8}]/td[{venue}]'
                                            )))
        venue_condition = check_venue.find_element(By.XPATH, './div/span')
        if venue_condition.text[:2] != "可约":
            return "不可订", venue_condition.text
        if venue_condition.text[2] == "1":
            if access_restriction:  # 上次被访问限制后，目标剩余场地为1，不应被选中，因此需要点击取消
                check_venue.click()
            return "不可订", "剩余场地为1"
        print(
            f"[{get_current_time()}] {order['person']}: {order['campus']}校区 {order['time_slot']} {venue}号 {venue_condition.text}")
        if not access_restriction:  # 上次被访问限制后，目标场地仍然可订且已被选中，因此不再点击
            check_venue.click()
        WebDriverWait(driver, time_out, check_frequency).until(
            ec.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div/section/div[1]/div[4]/div[2]/button'))
        ).click()

        accept_or_cancel_div = WebDriverWait(driver, time_out, check_frequency).until(
            ec.presence_of_element_located((By.XPATH, '//*[@id="app"]/div/div/section/div[3]/section/div')))

        accept = WebDriverWait(accept_or_cancel_div, time_out, check_frequency).until(
            ec.element_to_be_clickable((By.XPATH, ".//span[contains(text(), '接受')]")))

        # 此处使用信号量
        order["semaphore"]["remaining_ready"] -= 1
        while order["semaphore"]["remaining_ready"] > 0:
            pass
        accept.click()
        try:
            WebDriverWait(driver, time_out, check_frequency).until(ec.title_is("选择数量"))
            break
        except selenium.common.exceptions.TimeoutException:
            print(f"[{get_current_time()}] {order['person']}: {order['campus']}校区 受到访问限制")
            access_restriction = True
            time.sleep(max(60, 60 - time_out))
            driver.refresh()

    temp_ele = WebDriverWait(driver, time_out, check_frequency).until(
        ec.presence_of_element_located((By.XPATH, '//*[@id="app"]/div/div/div/section')))

    WebDriverWait(temp_ele, time_out, check_frequency).until(
        ec.element_to_be_clickable((By.XPATH,
                                    './div[1]/div/div[3]/div/div[2]/span[2]'))
    ).click()

    WebDriverWait(temp_ele, time_out, check_frequency).until(
        ec.element_to_be_clickable((By.XPATH,
                                    './div[2]/div[2]/button'))
    ).click()
    waiting_time = 0
    while waiting_time < time_out * 10:
        if driver.title == "支付成功":
            return "成功", "已完成"
        try:
            failure = driver.find_element(By.XPATH, '/html/body/div[4]/div')
            return "失败", failure.text
        except NoSuchElementException:
            pass
        time.sleep(check_frequency)
        waiting_time += 1
    print(f"[{get_current_time()}] 临时信息: {order['person']}: {order['campus']}校区:怎么会执行到这一行？")
    driver.save_screenshot(f"{get_current_time()} {order['person']}.png")
    return "成功", "结果不确定，需手动检查"


def booking(order):
    driver = init_driver(order)
    person = order["person"]
    time_slot = order["time_slot"]
    campus = order["campus"]
    venue = order["venue"]
    sqc = grt_sqc(campus, venue)
    try:
        WebDriverWait(driver, time_out, check_frequency).until(
            ec.presence_of_element_located((By.XPATH, '//*[@id="app"]/div/div/section/section/div[1]')))
    except selenium.common.exceptions.TimeoutException as e:
        print(f"[{get_current_time()}] {person}: 登录{campus}校区失败！:{e}")  # 有小概率登录失败
        return
    else:
        print(f"[{get_current_time()}] {person}: 已登录{campus}校区")

    driver.get(CL[campus])

    # 点击明日场地
    WebDriverWait(driver, time_out, check_frequency).until(
        ec.element_to_be_clickable((By.XPATH,
                                    '//*[@id="app"]/div/div/section/div[1]/div[2]/div[2]/div/ul/li[2]'))
    ).click()

    wt_venue = WebDriverWait(driver, time_out, check_frequency).until(
        ec.presence_of_element_located((By.XPATH,
                                        f'/html/body/div[2]/div/div/section/div[1]/div[3]/div/div[3]/table/tbody/tr[{int(order["time_slot"][0:2]) - 8}]/td[{venue}]'
                                        )))
    # 等待到07:00前
    waiting_until(booking_time)
    print(f"[{get_current_time()}] {person}: {campus}校区 监听场地信息更新")
    while wt_venue.find_element(By.XPATH, './div/span').text[-4:] == "开放预订":
        pass  # 等待场地自动刷新，无需使用driver.refresh()手动刷新
    print(f"[{get_current_time()}(+{time.time() % 1 // 0.01 / 100})] {person}: {campus}校区 开始订场")

    for i in sqc:
        result = booking_venue(driver, order, i)
        if result[0] == "成功":
            print(f"[{get_current_time()}] {person}: 订场 {campus}校区 {time_slot} {i}号 {result[1]}")
            save_qrcode(driver, order["person"])
            return
        if result[0] == "失败":
            driver.get(CL[campus])  # 不使用driver.back()的原因是，上一次订场失败的弹窗会保留导致检测错误
        if i == venue:
            print(f"[{get_current_time()}] {person}: 订场 {campus}校区 {time_slot} {i}号 {result[0]}，原因：{result[1]}")
            print(f"[{get_current_time()}] {person}: 改订{campus}校区同一时段的其他场地")
    order["semaphore"]["remaining_ready"] -= 1
    print(f"[{get_current_time()}] {person}: {campus}校区同一时段的其他场地均不可订")
    # 补订似乎没什么用，所以删掉了

