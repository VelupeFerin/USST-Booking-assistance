import nodriver as nd

async def main():
    input("即将打开Chrome浏览器，并跳转到https://usst.ydmap.cn/user/my，请登录然后回到此处。点击Enter继续")
    browser = await nd.start()
    await browser.get('https://usst.ydmap.cn/user/my')
    cookies_file_name = input("请命名您的cookies：")
    await browser.cookies.save(cookies_file_name+'.cookies')
    browser.stop()
    input("接下来要检查cookies的正确性,浏览器打开后，回到此处。点击Enter继续")
    browser = await nd.start()
    await browser.get('https://usst.ydmap.cn/user/my')
    await browser.cookies.load(cookies_file_name+'.cookies')
    input("如果在“个人中心”发现您已登录，那么刚才导出的cookies是正确的。点击Enter关闭")
    browser.stop()
if __name__ == '__main__':
    nd.loop().run_until_complete(main())