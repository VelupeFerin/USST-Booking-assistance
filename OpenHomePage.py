import time
from threading import Thread

from selenium.common.exceptions import SessionNotCreatedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

from booking_thread import send_cookie
from undetected_chromedriver import Chrome

"""
这些代码用于打开某人的主页
"""

name_list = ['fyq']
# name_list = ['wcc']


def open_browser(name):
    # driver = Chrome(driver_executable_path='./UndetectedChromedriver/chromedriver.exe')
    driver = Chrome()

    # try:
    #     driver = Chrome(
    #         driver_executable_path='C:/Users/asus/AppData/Roaming/chromedriver/chromedriver.exe')
    # except FileNotFoundError:
    #     print("驱动未找到，下载最新undetected_chromedriver")
    #     driver = Chrome()
    #     print("下载完成")
    # except SessionNotCreatedException:
    #     print("Chrome 更新，下载最新undetected_chromedriver")
    #     driver = Chrome()
    #     print("下载完成")

    driver.maximize_window()
    driver.get("https://usst.ydmap.cn")
    send_cookie(driver, name)
    time.sleep(1)
    driver.get("https://usst.ydmap.cn/order2?orderState=toUse")

    time.sleep(100000)


if __name__ == '__main__':
    for i in name_list:
        Thread(target=open_browser, args=(i,)).start()
    exit(0)
