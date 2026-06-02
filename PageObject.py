from string import Template

from elem_utils import *
import asyncio

class BasePageObject:
    venue_516_url = 'https://usst.ydmap.cn/booking/schedule/102285?salesItemId=102831'
    venue_1100_url = 'https://usst.ydmap.cn/booking/schedule/102293?salesItemId=102829'
    user_my_url = 'https://usst.ydmap.cn/user/my'

    def __init__(self,browser):
        self.browser = browser

    async def get_venue_page(self,venue):
        if venue == '516':
            tab = await self.browser.get(self.venue_516_url)
        elif venue == '1100':
            tab = await self.browser.get(self.venue_1100_url)
        else:
            tab = None
        return tab

    async def get_my_page(self):
        return await self.browser.get(self.user_my_url)

class UserInfoPageObject:
    username_xpath = '/html/body/div[1]/div/div[1]/section/section/div[1]/div[1]/div[2]/div[1]/span'

    def __init__(self,page):
        self.page = page

    async def get_username(self):
        return await get_elem_text(self.page, self.username_xpath)


class BookingSchedulePageObject:
    date_li_xpath = '/html/body/div[1]/div/div[1]/section/div[1]/div[2]/div[2]/div/ul/li[2]'
    target_session_xpath = Template('/html/body/div[1]/div/div[1]/section/div[1]/div[3]/div/div[3]/div[1]/table/tbody/tr[$t]/td[$f]')
    next_step_button_xpath = '/html/body/div[1]/div/div[1]/section/div[1]/div[4]/div[2]/button'
    confirm_button_section_xpath = '/html/body/div[1]/div/div[1]/section/div[3]/section/div'
    confirm_button_xpath= Template('/html/body/div[1]/div/div[1]/section/div[3]/section/div/div[$n]/button')

    def __init__(self,page):
        self.page = page

    async def wait_for_page_ready(self):
        await wait_for_page_ready(self.page)

    async def click_date(self):
        await wait_elem_and_click(self.page, self.date_li_xpath)

    async def waiting_session_open_and_select(self,t,f,timeout = 6):
        # print(f'[{get_current_time()}] waiting_session_open_and_select begin')
        tab = self.page
        rest_time = timeout
        while rest_time > 0:
            await wait_elem_and_click(tab, self.target_session_xpath.substitute(t=t, f=f))
            if await is_button_clickable(tab, self.next_step_button_xpath):
                await (await tab.find(self.next_step_button_xpath)).mouse_click()  # 使用mouse_click()可以绕过检测
                break
            else:
                await asyncio.sleep(0.1)
                rest_time -= 0.1
        if rest_time <= 0:
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

    async def get_session_snapshot_bytes(self,t,f):
        tab = self.page
        await elem_scroll_into_view(tab, self.target_session_xpath.substitute(t=t, f=f))
        canvas_xpath = self.target_session_xpath.substitute(t=t, f=f) + '/canvas'
        await wait_elem_exists(tab, canvas_xpath)
        return await get_canvas_bytes(tab,canvas_xpath)

class SessionNumberPageObject:
    add_session_number_button_xpath = '/html/body/div[1]/div/div[1]/div/section/div[1]/div/div[3]/div/div[2]/button[2]'
    session_number_xpath = '/html/body/div[1]/div/div[1]/div/section/div[1]/div/div[3]/div/div[1]/span'
    next_step_button_xpath = '/html/body/div[1]/div/div[1]/div/section/div[2]/div[2]/button'
    title_xpath = '/html/head/title'

    def __init__(self,page):
        self.page = page

    async def wait_for_page_ready(self):
        await wait_for_page_ready(self.page)

    async def click_add_session_number(self):
        # print(f'[{get_current_time()}] click_add_session_number begin')
        tab = self.page
        if (await wait_elem_text_exist_then_get(tab,self.session_number_xpath)).strip() == '1':
            return False
        else:
            await wait_elem_and_click(tab, self.add_session_number_button_xpath)
            # print(f'[{get_current_time()}] click_add_session_number end')
            return True

    async def click_next_step_button(self,timeout=3):
        # print(f'[{get_current_time()}] click_next_step_button begin')
        tab = self.page
        rest_time = timeout
        while rest_time > 0:
            try:
                await (await tab.find(self.next_step_button_xpath)).mouse_click()  # 点击后，按钮在会短暂消失（很短的时间），原因不明
                # print(f'[{get_current_time()}] click_next_step_button')
            except Exception:
                pass
            await asyncio.sleep(0.3)
            if await get_elem_text(tab,self.title_xpath) == '选择数量':
                rest_time -= 0.3
            else:
                break
        if rest_time <= 0:
            return False
        else:
            # print(f'[{get_current_time()}] click_next_step_button end')
            return True


class PaymentResultPageObject:
    title_xpath = '/html/head/title'
    order_detail_button_xpath = '/html/body/div[1]/div/div[1]/section/section/div/div/a/button'

    def __init__(self,page):
        self.page = page

    async def wait_for_page_ready(self,timeout = 5):
        return await wait_elem_text_equal_to(self.page, self.title_xpath,'支付成功',timeout)

    async def click_order_detail_button(self):
        await wait_elem_and_click(self.page, self.order_detail_button_xpath)


class OrderDetailPageObject:
    qrcode_canvas_xpath = '/html/body/div[1]/div/div[1]/div/div[1]/div[2]/div[1]/section/div[1]/div/div/div[4]/div[2]/div/div/div/div/div[2]/div/div[1]/div/div/div[2]/div[2]/div/canvas'
    order_info_xpath = '/html/body/div[1]/div/div[1]/div/div[1]/div[2]/div[1]/section/div[1]/div/div/div[1]/div[2]/div[1]/div[2]/div[2]/div[1]'
    order_id_xpath = '/html/body/div[1]/div/div[1]/div/div[1]/div[2]/div[1]/section/div[2]/div[1]/span'

    def __init__(self,page):
        self.page = page

    async def wait_for_page_ready(self):
        await wait_for_page_ready(self.page)

    async def get_order_id(self):
        return (await get_elem_text(self.page, self.order_id_xpath))[5:-1]

    async def get_order_info(self):
        return await get_elem_text(self.page, self.order_info_xpath)

    async def get_qrcode_bytes(self):
        await wait_elem_exists(self.page, self.qrcode_canvas_xpath)
        return await get_canvas_bytes(self.page,self.qrcode_canvas_xpath)