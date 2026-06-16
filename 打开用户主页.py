import os
import sys

import nodriver as nd


async def main():
    cookies_mapping = {}
    try:
        i=1
        for filename in os.listdir('Cookies'):
            if os.path.isfile(os.path.join('Cookies', filename)) and filename.endswith(".cookies"):
                cookies_mapping[i] = filename[0:-8]
                i+=1
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
        except (KeyError,ValueError):
            print(f"格式错误或没有此序号的cookies:{p_n}")
            continue
        if not os.path.exists(f'Cookies/{p}.cookies'):
            print(f'{p}.cookies 不存在')
            continue
        browser = await nd.start(browser_args=[f"--window-position={100 * i},0"])
        await browser.cookies.load(f"Cookies/{p}.cookies")
        await browser.get('https://usst.ydmap.cn/user/my')
        i += 1


if __name__ == '__main__':
    # os.chdir(os.path.dirname(sys.executable))
    nd.loop().run_until_complete(main())
    input()
