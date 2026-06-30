from string import Template

from browser_utils import simple_http_get
from elem_utils import *
import asyncio

from time_utils import get_current_time


class BasePageObject:
    venue_516_url = 'https://usst.ydmap.cn/booking/schedule/102285?salesItemId=102831'
    venue_1100_url = 'https://usst.ydmap.cn/booking/schedule/102293?salesItemId=102829'
    user_my_url = 'https://usst.ydmap.cn/user/my'
    login_url = 'https://usst.ydmap.cn/user/login'

    title_xpath = '/html/head/title'
    venue_str_url_dict = {'516': venue_516_url, '1100': venue_1100_url}

    def __init__(self, page):
        self.page = page

    async def is_page_exist(self):
        try:
            target_infos = await self.page.browser.send(nd.cdp.target.get_targets())
            current_page_target_id = self.page.target_id
            for target_info in target_infos:
                if current_page_target_id == target_info.target_id:
                    return True
        except Exception:
            pass  # 若浏览器已关闭或连接异常，则视为标签页不存在
        return False

    async def get_venue_page(self, venue_str):
        url = self.venue_str_url_dict.get(venue_str)
        return BookingSchedulePageObject(await self.page.get(url)) if url else None

    async def get_my_info_page(self):
        return UserInfoPageObject(await self.page.get(self.user_my_url))

    async def get_login_page(self):
        return LoginPageObject(await self.page.get(self.login_url))

    async def get_server_timestamp(self):
        return (await simple_http_get(self.page, '/srv100308/api/pub/tool/getSysDate'))['timestamp']

    async def waiting_server_time_until(self, target_time, recheck: bool = True):
        """
        异步等待，直到远程服务器时间达到或超过指定的目标时间。
        :param target_time: 目标时间点，视为本地时区。假设服务器与本地机器处于同一时区。
        :param recheck:     若为 True，则在首次等待结束后循环检查，直到确认服务器时间已超过目标；
                             若为 False，则仅等待一次计算出的时长后直接返回。
        :return:            无返回值
        """
        target_ts_ms = int(target_time.timestamp() * 1000)
        server_ts_ms = await self.get_server_timestamp()
        wait_ms = target_ts_ms - server_ts_ms
        if wait_ms <= 0:
            return
        await asyncio.sleep(wait_ms / 1000.0)
        if not recheck:
            return
        while True:
            current_server_ts = await self.get_server_timestamp()
            if current_server_ts >= target_ts_ms:
                break
            remaining_ms = target_ts_ms - current_server_ts
            await asyncio.sleep(remaining_ms / 1000.0)


class LoginPageObject(BasePageObject):

    def __init__(self, page):
        super().__init__(page)

    async def wait_login(self):
        tab = self.page
        while await self.is_page_exist():
            if await get_elem_text(tab, self.title_xpath) == UserInfoPageObject.page_expected_title:
                return UserInfoPageObject(tab)
            else:
                await asyncio.sleep(0.5)
        return None


class UserInfoPageObject(BasePageObject):
    page_expected_title = '个人中心'
    username_xpath = '/html/body/div[1]/div/div[1]/section/section/div[1]/div[1]/div[2]/div[1]/span'

    def __init__(self, page):
        super().__init__(page)

    async def wait_username_then_get(self, retry=20):
        i = retry
        while i > 0 and await self.is_page_exist():
            username = await get_elem_text(self.page, self.username_xpath)
            if username == '--' or username == '':
                await asyncio.sleep(0.5)
                i -= 1
            else:
                return username
        return None


class BookingSchedulePageObject(BasePageObject):
    date_li_xpath = '/html/body/div[1]/div/div[1]/section/div[1]/div[2]/div[2]/div/div/ul/li[2]'
    target_session_xpath = Template(
        '/html/body/div[1]/div/div[1]/section/div[1]/div[3]/div/div[3]/div[1]/table/tbody/tr[$t]/td[$f]')
    next_step_button_xpath = '/html/body/div[1]/div/div[1]/section/div[1]/div[4]/div[2]/button'
    confirm_button_section_xpath = '/html/body/div[1]/div/div[1]/section/div[3]/section/div'
    confirm_button_xpath = Template('/html/body/div[1]/div/div[1]/section/div[3]/section/div/div[$n]/button')

    def __init__(self, page):
        super().__init__(page)

    async def wait_for_page_ready(self):
        await wait_for_page_ready(self.page)

    async def select_date(self):
        await wait_elem_and_click(self.page, self.date_li_xpath)

    # async def select_sessions(self, t, f, retry=60):
    async def select_sessions(self, target_sessions):
        # print(f'[{get_current_time()}] waiting_session_open_and_select begin')
        tab = self.page
        for s in target_sessions:
            await wait_elem_and_click(tab, self.target_session_xpath.substitute(t=s[0], f=s[1]))
        # 从localStorage获取被点击且被选择的场次
        ss = await tab.evaluate(
            "JSON.parse(localStorage.getItem('select-cols-cache')).cols.map((item)=>{{return item.key;}});")
        ss_set = set()
        if len(ss) > 0:
            for i in ss:
                t, f = i['value'].split('-')
                ss_set.add((int(t) + 1, int(f) + 1))
        return ss_set
        # print(f'[{get_current_time()}] waiting_session_open_and_select end')

    async def click_next_step_button(self):
        tab = self.page
        if await is_button_clickable(tab, self.next_step_button_xpath):
            await (await tab.find(self.next_step_button_xpath)).mouse_click()  # 使用mouse_click()可以绕过检测
            return True
        else:
            return False

    async def confirm_box_click(self):
        # print(f'[{get_current_time()}] confirm_box_click begin')
        tab = self.page
        button_section_text = await wait_elem_text_exist_then_get(tab, self.confirm_button_section_xpath)
        n = '1' if button_section_text == ' 接受  返回 ' else '2'
        await (await tab.find(self.confirm_button_xpath.substitute(n=n))).mouse_click()
        # print(f'[{get_current_time()}] confirm_box_click end')
        return SessionNumberPageObject(tab)

    async def get_session_snapshot_bytes(self, t, f):
        tab = self.page
        await elem_scroll_into_view(tab, self.target_session_xpath.substitute(t=t, f=f))
        canvas_xpath = self.target_session_xpath.substitute(t=t, f=f) + '/canvas'
        await wait_elem_exists(tab, canvas_xpath)
        return await get_canvas_bytes(tab, canvas_xpath)


class SessionNumberPageObject(BasePageObject):
    session_number_xpath = '/html/body/div[1]/div/div[1]/div/section/div[1]/div/div[3]/div/div[1]/span'
    session_number_input_xpath = '/html/body/div[1]/div/div[1]/div/section/div[1]/div/div[3]/div/div[2]/input'
    next_step_button_xpath = '/html/body/div[1]/div/div[1]/div/section/div[2]/div[2]/button'

    def __init__(self, page):
        super().__init__(page)

    async def wait_for_page_ready(self):
        await wait_for_page_ready(self.page)

    async def set_session_number(self, n):
        # print(f'[{get_current_time()}] click_add_session_number begin')
        tab = self.page
        if int((await wait_elem_text_exist_then_get(tab, self.session_number_xpath)).strip()) < n:
            return False
        else:
            await fill_elem_text(tab, self.session_number_input_xpath, str(n))
            # print(f'[{get_current_time()}] set_session_number end')
            return True

    async def click_next_step_button(self, retry=10):
        # print(f'[{get_current_time()}] click_next_step_button begin')
        tab = self.page
        rest_click_times = retry
        while rest_click_times > 0:
            try:
                await(await tab.find(self.next_step_button_xpath, timeout=0.5)).mouse_click()
                # 点击后，按钮会短暂消失（很短的时间），原因不明
            except Exception:
                pass
            if (await get_elem_text(tab, self.title_xpath)) == PaymentResultPageObject.page_expected_title:
                # 这里可以加一个url的格式检查，但没必要（因为url先于title加载完成）
                break
            else:
                rest_click_times -= 1
        if rest_click_times <= 0:
            return None
        else:
            # print(f'[{get_current_time()}] click_next_step_button end')
            return PaymentResultPageObject(tab)


class PaymentResultPageObject(BasePageObject):
    page_expected_title = '支付成功'
    order_detail_button_xpath = '/html/body/div[1]/div/div[1]/section/section/div/div/a/button'

    def __init__(self, page):
        super().__init__(page)

    async def get_order_detail_page_by_url(self):
        await self.page.evaluate(
            "window.location.href = window.location.href.replace('/pay/', '/order/').replace(/\\/result$/, '')")
        # 用js在浏览器中把支付结果url转换为订单详情url，并转到此url
        return OrderDetailPageObject(self.page)


class OrderDetailPageObject(BasePageObject):
    qrcode_canvas_xpath = '/html/body/div[1]/div/div[1]/div/div[1]/div[2]/div[1]/section/div[1]/div/div/div[4]/div[2]/div/div/div/div/div[2]/div/div[1]/div/div/div[2]/div[2]/div/canvas'
    order_info_xpath = '/html/body/div[1]/div/div[1]/div/div[1]/div[2]/div[1]/section/div[1]/div/div/div[1]/div[2]/div[1]/div[2]/div[2]/div[1]'
    order_id_xpath = '/html/body/div[1]/div/div[1]/div/div[1]/div[2]/div[1]/section/div[2]/div[1]/span'

    def __init__(self, page):
        super().__init__(page)

    async def wait_for_page_ready(self):
        await wait_for_page_ready(self.page)

    async def get_order_id(self):
        return (await get_elem_text(self.page, self.order_id_xpath))[5:-1]

    async def get_order_info(self):
        return await get_elem_text(self.page, self.order_info_xpath)

    async def get_qrcode_bytes(self):
        await wait_elem_exists(self.page, self.qrcode_canvas_xpath, timeout=15)
        return await get_canvas_bytes(self.page, self.qrcode_canvas_xpath)
