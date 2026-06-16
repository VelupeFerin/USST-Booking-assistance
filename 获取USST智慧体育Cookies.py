import os
import subprocess
import sys
import ctypes
import nodriver as nd

import PageObject

message_box_title = "获取USST智慧体育Cookies"
MB_OK = 0x00000000  # 显示“确定”按钮
MB_OKCANCEL = 0x00000001  # 显示“确定”和“取消”按钮
MB_RETRYCANCEL = 0x00000005  # 显示“重试”和“取消”按钮
MB_ICONINFORMATION = 0x00000040  # 信息图标
MB_ICONWARNING = 0x00000030  # 警告图标
DIALOG_RESULT_CANCEL = 2  # 选择“取消”或点击右上角关闭


async def main():
    os.chdir(os.path.dirname(sys.executable))
    user32 = ctypes.windll.user32
    dialog_choice = user32.MessageBoxW(
        0,
        "即将打开Chrome浏览器，并跳转到USST智慧体育登录页面。请登录以导出cookies。\n浏览器由本程序打开，若未打开则可能没有安装Chrome或打开过程中出现问题。\n点击“确定”继续",
        message_box_title,
        MB_OKCANCEL | MB_ICONINFORMATION
    )
    while dialog_choice != DIALOG_RESULT_CANCEL:
        browser = await nd.start()
        bp = PageObject.BasePageObject(browser.main_tab)
        lp = await bp.get_login_page()
        uip = await lp.wait_login()

        if uip is None:
            username = None
        else:
            username = await uip.wait_username_then_get()

        if username is None:
            browser.stop()
            dialog_choice = user32.MessageBoxW(
                0,
                "出现错误，可能没有成功登录或浏览器被关闭。请重试",
                message_box_title,
                MB_RETRYCANCEL | MB_ICONWARNING
            )
        else:
            await browser.cookies.save(username + '.cookies')
            browser.stop()
            subprocess.Popen(['explorer', '/select,', username + '.cookies'])
            user32.MessageBoxW(
                0,
                "cookies已保存。",
                message_box_title,
                MB_OK | MB_ICONINFORMATION
            )
            return


if __name__ == '__main__':
    nd.loop().run_until_complete(main())
