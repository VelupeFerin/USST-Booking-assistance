from string import Template

from elem_utils import *
import asyncio

from time_utils import get_current_time


class BasePageObject:
    venue_516_url = 'https://usst.ydmap.cn/booking/schedule/102285?salesItemId=102831'
    venue_1100_url = 'https://usst.ydmap.cn/booking/schedule/102293?salesItemId=102829'
    user_my_url = 'https://usst.ydmap.cn/user/my'
    login_url = 'https://usst.ydmap.cn/user/login'

    title_xpath = '/html/head/title'
    venue_str_url_dict = {'516':venue_516_url, '1100':venue_1100_url}

    def __init__(self, page):
        self.page = page

    async def get_venue_page(self, venue_str):
        url = self.venue_str_url_dict.get(venue_str)
        return BookingSchedulePageObject(await self.page.get(url)) if url else None

    async def get_my_info_page(self):
        return UserInfoPageObject(await self.page.get(self.user_my_url))

    async def get_login_page(self):
        return LoginPageObject(await self.page.get(self.login_url))

class LoginPageObject(BasePageObject):

    def __init__(self, page):
        super().__init__(page)

    async def wait_login(self):
        tab = self.page
        while not (await get_elem_text(tab, self.title_xpath) == UserInfoPageObject.page_expected_title):
            await asyncio.sleep(0.5)
        return UserInfoPageObject(tab)


class UserInfoPageObject(BasePageObject):
    page_expected_title = '个人中心'
    username_xpath = '/html/body/div[1]/div/div[1]/section/section/div[1]/div[1]/div[2]/div[1]/span'

    def __init__(self, page):
        super().__init__(page)

    async def wait_username_then_get(self,retry = 20):
        i = retry
        while i > 0:
            username = await get_elem_text(self.page, self.username_xpath)
            if username == '--' or username == '':
                await asyncio.sleep(0.5)
                i -= 1
            else:
                return username
        return None


class BookingSchedulePageObject(BasePageObject):
    date_li_xpath = '/html/body/div[1]/div/div[1]/section/div[1]/div[2]/div[2]/div/ul/li[2]'
    target_session_xpath = Template(
        '/html/body/div[1]/div/div[1]/section/div[1]/div[3]/div/div[3]/div[1]/table/tbody/tr[$t]/td[$f]')
    next_step_button_xpath = '/html/body/div[1]/div/div[1]/section/div[1]/div[4]/div[2]/button'
    confirm_button_section_xpath = '/html/body/div[1]/div/div[1]/section/div[3]/section/div'
    confirm_button_xpath = Template('/html/body/div[1]/div/div[1]/section/div[3]/section/div/div[$n]/button')

    def __init__(self, page):
        super().__init__(page)

    async def wait_for_page_ready(self):
        await wait_for_page_ready(self.page)

    async def click_date(self):
        await wait_elem_and_click(self.page, self.date_li_xpath)

    async def waiting_session_open_and_select(self, t, f, retry=60):
        # print(f'[{get_current_time()}] waiting_session_open_and_select begin')
        tab = self.page
        rest_click_times = retry
        while rest_click_times > 0:
            await wait_elem_and_click(tab, self.target_session_xpath.substitute(t=t, f=f))
            if await is_button_clickable(tab, self.next_step_button_xpath):
                await (await tab.find(self.next_step_button_xpath)).mouse_click()  # 使用mouse_click()可以绕过检测
                break
            else:
                await asyncio.sleep(0.1)
                rest_click_times -= 1
        if rest_click_times <= 0:
            return False
        else:
            # print(f'[{get_current_time()}] waiting_session_open_and_select end')
            return True

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
    add_session_number_button_xpath = '/html/body/div[1]/div/div[1]/div/section/div[1]/div/div[3]/div/div[2]/button[2]'
    session_number_xpath = '/html/body/div[1]/div/div[1]/div/section/div[1]/div/div[3]/div/div[1]/span'
    next_step_button_xpath = '/html/body/div[1]/div/div[1]/div/section/div[2]/div[2]/button'

    def __init__(self, page):
        super().__init__(page)

    async def wait_for_page_ready(self):
        await wait_for_page_ready(self.page)

    async def click_add_session_number(self):
        # print(f'[{get_current_time()}] click_add_session_number begin')
        tab = self.page
        if (await wait_elem_text_exist_then_get(tab, self.session_number_xpath)).strip() == '1':
            return False
        else:
            await wait_elem_and_click(tab, self.add_session_number_button_xpath)
            # print(f'[{get_current_time()}] click_add_session_number end')
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
