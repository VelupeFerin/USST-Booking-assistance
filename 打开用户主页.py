import os

import nodriver as nd


async def main():
    persons = input("请输入多个要用于打开主页的cookies名，用空格分隔：")
    i = 0
    for p in persons.split():
        if not os.path.exists(f'Cookies/{p}.cookies'):
            print(f'{p}.cookies 不存在')
            continue
        browser = await nd.start(browser_args=[f"--window-position={100 * i},0"])
        await browser.cookies.load(f"Cookies/{p}.cookies")
        await browser.get('https://usst.ydmap.cn/user/my')
        i += 1


if __name__ == '__main__':
    nd.loop().run_until_complete(main())
    input()
