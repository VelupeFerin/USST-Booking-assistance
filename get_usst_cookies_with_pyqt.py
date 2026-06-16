import sys
import asyncio
import os
import subprocess
import nodriver as nd
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt
from qasync import QEventLoop, asyncSlot

import PageObject


class GetUSSTCookiesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.main_text = QLabel()
        self.btn = QPushButton()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 主文本
        self.main_text.setText(
            "点击下方按钮打开 Chrome 浏览器，由本程序打开，无需手动打开。\n"
            "打开后将会跳转到USST智慧体育登录页面。\n"
            "请手动登录，然后等待程序自动继续。"
        )
        self.main_text.setWordWrap(True)
        self.main_text.setAlignment(Qt.AlignCenter)
        self.main_text.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(self.main_text)

        # 按钮
        self.btn.setText("打开浏览器")
        self.btn.clicked.connect(self.on_start_click)
        layout.addWidget(self.btn)

        self.setLayout(layout)
        self.setWindowTitle("USST智慧体育 - 获取Cookies")
        self.resize(500, 200)

    # ---------- 按钮点击事件 ----------
    @asyncSlot()
    async def on_start_click(self):
        # 如果按钮为“关闭”，则直接关闭窗口
        if self.btn.text() == "关闭":
            self.close()
            return

        # 否则执行任务
        self.btn.setEnabled(False)
        self.main_text.setText("正在等待登录，请稍候...")

        # 调用任务
        success = await self.run_task()

        if success:
            # 正常结束：按钮变为“关闭”
            self.btn.setText("关闭")
            self.btn.setEnabled(True)
        else:
            # 失败：恢复初始状态，允许重试
            self.btn.setText("打开浏览器")
            self.btn.setEnabled(True)
            # 错误信息已在 run_task 中设置

    # ---------- 核心异步任务 ----------
    async def run_task(self) -> bool:
        """
        执行完整的登录与 Cookies 保存流程。
        返回 True 表示成功，False 表示失败（需要重试）。
        """
        try:
            browser = await nd.start()
            bp = PageObject.BasePageObject(browser)
            lp = await bp.get_login_page()
            uip = await lp.wait_login()
            username = await uip.wait_username_then_get()
            if username is None:
                self.main_text.setText(
                    "错误：未能获取用户名。\n"
                    "可能没有成功登录\n"
                    "请重试。"
                )
                browser.stop()
                return False

            # 保存 Cookies
            await browser.cookies.save(username + '.cookies')
            # 打开资源管理器并定位到 Cookies 文件
            file_path = os.path.abspath(username + '.cookies')
            subprocess.Popen(['explorer', '/select,', file_path])

            # 关闭浏览器
            browser.stop()

            # 成功提示
            self.main_text.setText(
                f"Cookies 已保存为：{username}.cookies\n"
            )
            return True

        except Exception as e:
            # 捕获其他异常（如网络错误、PageObject 内部异常等）
            self.main_text.setText(
                f"发生异常：{str(e)}\n"
                "请重试。"
            )
            return False


if __name__ == '__main__':
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = GetUSSTCookiesWindow()
    window.show()

    with loop:
        loop.run_forever()