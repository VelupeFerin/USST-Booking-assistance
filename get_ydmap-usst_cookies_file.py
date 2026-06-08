import nodriver as nd


async def main():
    input(
        "即将打开Chrome浏览器（由本程序打开，若未打开则说明没有安装Chrome或打开过程中出现问题），并跳转到USST智慧体育个人中心。请登录然后回到此处。点击Enter继续")
    browser = await nd.start()
    await browser.get('https://usst.ydmap.cn/user/my')
    cookies_file_name = input("请命名您的cookies：")
    await browser.cookies.save(cookies_file_name + '.cookies')
    browser.stop()
    input("您的cookies已保存到本程序所在文件夹\n接下来要检查cookies的正确性,浏览器打开后，回到此处。点击Enter继续")
    browser = await nd.start()
    await browser.get('https://usst.ydmap.cn/user/my')
    await browser.cookies.load(cookies_file_name + '.cookies')
    input("如果在“个人中心”发现您已登录，那么刚才导出的cookies是正确的。点击Enter关闭")
    browser.stop()


if __name__ == '__main__':
    nd.loop().run_until_complete(main())
