#
# RMUTI Network Account Service Kiosk
#
# Copyright: Prakai Nadee, 2019-2020
# Author:
#   Prakai Nadee <prakai@rmuti.ac.th>
#   Computer Engineering
#   Rajamangala University of Technology Isan
#

#
# Version number
NAS_KIOSK_VERSION = '1.02'

# System libraries
import os, sys, time, requests, json, re, base64
# from Crypto.Cipher import AES

# Application environment
APP_FOLDER_NAME = os.path.abspath(os.path.dirname(__file__))
os.environ['APP_FOLDER_NAME'] = APP_FOLDER_NAME
os.environ['KIVY_HOME'] = APP_FOLDER_NAME

# Logging
#os.environ['KIVY_NO_FILELOG'] = '1'
#os.environ['KIVY_NO_CONSOLELOG'] = '1'
#os.environ['KCFG_KIVY_LOG_LEVEL'] = 'WARNING'


# Application configuration
# Add the following 2 lines to solve OpenGL 2.0 bug
from kivy import Config
Config.set('graphics', 'multisamples', 0)
#Config.set('graphics', 'fullscreen', 'auto')
#Config.set('graphics', 'window_state', 'maximized')
Config.set('graphics', 'allow_screensaver', 0)
Config.set('kivy', 'exit_on_escape', 0)
#Config.set('kivy', 'keyboard_mode', 'dock')

Config.set('kivy','window_icon',APP_FOLDER_NAME+'\\lib\\resources\\Type-64.ico')

Config.set('kivy','log_dir', APP_FOLDER_NAME+'\\logs')
Config.set('kivy','log_name', 'NAS-Kiosk-%Y-%m-%d-%_.txt')

Config.set('kivy', 'default_font', [
    'SukhumvitSet',
    APP_FOLDER_NAME+'\\lib\\resources\\SukhumvitSet-Medium.ttf',
    APP_FOLDER_NAME+'\\lib\\resources\\SukhumvitSet-Medium.ttf',
    APP_FOLDER_NAME+'\\lib\\resources\\SukhumvitSet-Bold.ttf',
    APP_FOLDER_NAME+'\\lib\\resources\\SukhumvitSet-Bold.ttf',
])

# Kivy library
import kivy
kivy.require('1.11.1')

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.metrics import dp
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.image import AsyncImage
from kivy.uix.carousel import Carousel
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition, FadeTransition, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_hex_from_color

# KivyMD library
from kivymd.app import MDApp

from kivymd.font_definitions import theme_font_styles
from kivymd.icon_definitions import md_icons
from kivymd.uix.behaviors import HoverBehavior
from kivymd.uix.dialog import MDDialog, MDCard
from kivymd.uix.snackbar import Snackbar
from kivy.core.window import Window
#window size
Window.size = (400, 235)
# Thailand National ID Card reader
from lib.ThaiNationalIDCard import ThaiIDCard

class MDCardHover(HoverBehavior, MDCard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MDCardButton(ButtonBehavior, MDCardHover):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class ScrollableLabel(ScrollView):
    text = StringProperty('')
    font_name = StringProperty(LabelBase._fonts[DEFAULT_FONT][0])
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class SmartCardBehavior(ThaiIDCard):

    # Initial inserted Citizen ID
    last_citizen = None

    _clock = None
    
    _dialog = None
    
    smart_card_ready = None
    smart_card_wait_time_fore_reinsert = 20

    smart_card_remove = False
    smart_card_remove_dialog = None

    smart_card_change = False
    smart_card_change_dialog = None

    smart_card_removable = True
    smart_card_removable_dialog = None

    smart_card_wait_for_remove = False

    _reader_added_cb = None
    _reader_removed_cb = None

    _card_insert_cb = None
    _card_insert_tmp_cb = None
    _card_remove_cb = None
    _card_reinsert_cb = None
    _card_remove_forever_cb = None

    _card_removable = False
    _card_removable_tmp = False
    _wait_for_pull_out = False
    _wait_for_pull_out_tmp = False

    def __init__(self, screen, **kwargs):
        super().__init__()

        if(screen!=''):
            self.name = screen
        else:
            return None

        self._reader_added_cb = 'reader_added_callback' in kwargs.keys() and kwargs['reader_added_callback'] or None
        self._reader_removed_cb = 'reader_removed_callback' in kwargs.keys() and kwargs['reader_removed_callback'] or None

        self._card_insert_cb = 'card_insert_callback' in kwargs.keys() and kwargs['card_insert_callback'] or None
        self._card_remove_cb = 'card_remove_callback' in kwargs.keys() and kwargs['card_remove_callback'] or None

        self._card_reinsert_cb = 'card_reinsert_callback' in kwargs.keys() and kwargs['card_reinsert_callback'] or None
        self._card_remove_forever_cb = 'card_remove_forever_callback' in kwargs.keys() and kwargs['card_remove_forever_callback'] or None
        self._card_removable = 'card_removable' in kwargs.keys() and kwargs['card_removable'] or False
        self._card_removable_tmp = self._card_removable

    def monitor(self, t, citizen=None):
        # Save initial inserted Citizen ID
        self.last_citizen = citizen

        Logger.info('SmartCard: Add SmartCard observer')
        self.cardMonitor(self.smart_card_insert, self.smart_card_remove)

        #self.monitor_time = t
        #self._clock = Clock.schedule_once(self.check_smart_card, self.monitor_time)

    def unmonitor(self):
        self.last_citizen = None

        Logger.info('SmartCard: Remove SmartCard observer')
        self.cardUnMonitor()

        #self._clock.cancel()

    def reject(self):
        #self._clock.cancel()
        #self._card_removable = True
        self._wait_for_pull_out_tmp = self._wait_for_pull_out
        self._wait_for_pull_out = True

        Logger.info('SmartCard: Screen - ' + CPECafe.screen_manager.current + ', ' + self.name)

        if self._wait_for_pull_out:
            Logger.info('SmartCard: Waiting for remove a smart card')
            
            CPECafe.tsc.smart_card_removable_dialog = MDDialog(
                title='แจ้งให้ทราบ...',
                size=('380dp', '160dp'),
                size_hint=(None, None),
                #text="Thank you for using our service. Please pull out your Citizen Card to finish.",
                text="ขอบคุณที่ใช้บริการของเรา กรุณาถอดบัตรประจำตัวประชาชน",
                text_button_ok='Ok',
                auto_dismiss=False,
                events_callback=self.wait_for_pull_card_out_dialog_callback)
            CPECafe.tsc.smart_card_removable_dialog.open()

            if self.smart_card_removable == False:
                self.smart_card_removable = True
                self.smart_card_wait_for_remove = True
                
        #self._clock = Clock.schedule_once(self.check_smart_card, 2)
        
    def dialog(self, **kwargs):
        kwargs.update({'events_callback': self.dialog_callback})
        self._dialog = MDDialog(**kwargs)
        self._dialog.open()

    def dialog_callback(self, *args):
        self._dialog = None

    def smart_card_insert(self):
        Logger.info('SmartCard: Reading data from SmartCard...')

        Logger.info('SmartCard: Screen - ' + CPECafe.screen_manager.current + ', ' + self.name)

        if CPECafe.screen_manager.current != self.name:
            return

        if self.connect(self.readerIndex) != None:
            Logger.info('SmartCard: Connected and read data from SmartCard')
            
            Logger.info('SmartCard: Last Citizen=%s'%(self.last_citizen))
            Logger.info('SmartCard: Citizen=%s'%(self.citizen))

            if self.last_citizen!=None and self.last_citizen!=self.citizen:
                #Logger.info('SmartCard: R1')
                if self.smart_card_change == False:
                    if self.smart_card_remove:
                        CPECafe.tsc.smart_card_remove_dialog.dismiss(force=True)
                        CPECafe.tsc.smart_card_remove_dialog = None
                        self.smart_card_remove = False
                        Clock.unschedule(self.check_smart_card_away)

                    self.smart_card_change = True
                    CPECafe.tsc.smart_card_change_dialog = MDDialog(
                        title='แจ้งเตือน...',
                        size=('480dp', '260dp'),
                        size_hint=(None, None),
                        #text="Your Citizen Card was pulled out. Please reinsert your Citizen Card to continue or click 'Cancel' to cancel.",
                        text="พบว่ามีการเปลี่ยนบัตรประจำตัวประชาชน กรุณาเสียบบัตรประจำตัวประชาชนเดิมเพื่อดำเนินการต่อ หรือเลือก 'Cancel' เพื่อสิ้นสุดการดำเนินการ",
                        text_button_ok='OK',
                        text_button_cancel='Cancel',
                        auto_dismiss=False,
                        events_callback=self.smart_card_remove_dialog_callback)
                    CPECafe.tsc.smart_card_change_dialog.open()
            else:
                #Logger.info('SmartCard: R2')
                if self._card_insert_cb != None:
                    self._card_insert_cb()
                    return

                if self._wait_for_pull_out:
                    Logger.info('SmartCard: Waiting to pull out the card')
                    if self.smart_card_removable == False:
                        self.smart_card_removable = True
                        CPECafe.tsc.smart_card_removable_dialog = MDDialog(
                            title='แจ้งให้ทราบ...',
                            size=('480dp', '280dp'),
                            size_hint=(None, None),
                            #text="Thank you for using our service. Please pull out your Citizen Card to finish.",
                            text="ขอบคุณที่ใช้บริการของเรา กรุณาถอดบัตรประจำตัวประชาชนออกจากช่องอ่านบัตรเพื่อสิ้นสุดการดำเนินการ",
                            text_button_ok='Ok',
                            auto_dismiss=False,
                            events_callback=self.wait_for_pull_card_out_dialog_callback)
                        CPECafe.tsc.smart_card_removable_dialog.open()

                elif self.smart_card_remove:
                    CPECafe.tsc.smart_card_remove_dialog.dismiss(force=True)
                    CPECafe.tsc.smart_card_remove_dialog = None
                    self.smart_card_remove = False
                    Clock.unschedule(self.check_smart_card_away)

                    if self._card_reinsert_cb != None:
                        self._card_reinsert_cb()
        else:
            Logger.info('SmartCard: Error reading SmartCard')

    def smart_card_remove(self):
        Logger.info('SmartCard: SmartCard removed...')
        
        Logger.info('SmartCard: Screen - ' + CPECafe.screen_manager.current + ', ' + self.name)

        self.disconnect()
        
        if self.smart_card_change:
            self.smart_card_change_dialog.dismiss(force=True)
            self.smart_card_change = False

        if self._card_remove_cb != None:
            self._card_remove_cb()
        elif self._card_removable == True:
            self.smart_card_remove_dialog_callback('Cancel')
        elif self._wait_for_pull_out == True:
            self.smart_card_remove_dialog_callback('Cancel')
        elif self.smart_card_removable == True:
            self.smart_card_remove_dialog_callback('Cancel')
        elif self.smart_card_remove == False:
            #Clock.schedule_once(self.check_smart_card_away, self.smart_card_wait_time_fore_reinsert)
            self.smart_card_remove = True
            CPECafe.tsc.smart_card_remove_dialog = MDDialog(
                title='แจ้งเตือน...',
                size=('480dp', '260dp'),
                size_hint=(None, None),
                #text="Your Citizen Card was pulled out. Please reinsert your Citizen Card to continue or click 'Cancel' to cancel.",
                text="มีการถอดบัตรประจำตัวประชาชนออกช่องอ่านบัตร กรุณาเสียบบัตรประจำตัวประชาชนเพื่อดำเนินการต่อ หรือเลือก 'Cancel' เพื่อสิ้นสุดการดำเนินการ",
                text_button_ok='OK',
                text_button_cancel='Cancel',
                auto_dismiss=False,
                events_callback=self.smart_card_remove_dialog_callback)
            CPECafe.tsc.smart_card_remove_dialog.open()

    def check_smart_card_away(self, instance):
        Logger.info('SmartCard: Timeout to wait for re-insert Citizen Card, then return to Home screen')
        self.smart_card_remove_dialog_callback('Cancel')

    def wait_for_pull_card_out_dialog_callback(self, *args):
        if(args[0]=='Ok'):
            #self._clock.cancel()
            self.smart_card_removable = False
            #self._clock = Clock.schedule_once(self.check_smart_card, 1)

    def smart_card_remove_dialog_callback(self, *args):
        #Clock.unschedule(self.check_smart_card_away)
        if(args[0]=='Cancel'):
            Logger.info('SmartCard: Hide active dialog')

            if self._dialog != None:
                self._dialog.dismiss(force=True)
                self._dialog = None
            
            if self.smart_card_change:
                CPECafe.tsc.smart_card_change_dialog.dismiss(force=True)
            
            if CPECafe.tsc.smart_card_removable_dialog != None:
                CPECafe.tsc.smart_card_removable_dialog.dismiss(force=True)

            if self._card_remove_cb != None:
                self._card_remove_forever_cb()

            self._card_removable = self._card_removable_tmp
            self._wait_for_pull_out = self._wait_for_pull_out_tmp

            CPECafe.screen_manager.transition = SlideTransition(direction='right')
            #CPECafe.home_page.smartcard_text.text = f'Please insert your Citizen Card'
            CPECafe.home_page.smartcard_text.text = f'กรุณาเสียบบัตรประจำตัวประชาชน'
            #CPECafe.home_page.smartcard_image.source = f'lib\\resources\\insert_credit_card2_512px.png'
            CPECafe.screen_manager.current = 'Home'
            #CPECafe.tsc.monitor(4)
            CPECafe.tsc.smart_card_remove_dialog = None
            self.smart_card_remove = False
            self.smart_card_change = False
            self.smart_card_removable = True
            self.smart_card_wait_for_remove = False
            self.last_citizen = None
        else:
            CPECafe.tsc.smart_card_remove_dialog = None
            self.smart_card_remove = False
            #self.smart_card_change = False
            #self.smart_card_removable = False


class LoadingPage(GridLayout):

    progress_text = ObjectProperty(None)
    progress_bar = ObjectProperty(None)
    progress_max = 4
    progress = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        #self.load_pages()

    def load_pages(self):

        with open(f'lib\\Home.kv', encoding='utf8') as f:
            Builder.load_string(f.read())
        CPECafe.home_page = HomePage()
        screen = Screen(name='Home')
        screen.add_widget(CPECafe.home_page)
        CPECafe.screen_manager.add_widget(screen)

        self.progress_bar.text = f'Loading: Home Screen...'
        self.progress = self.progress + 1
        self.progress_bar.value = (self.progress/self.progress_max)*100

        with open(f'lib\\RegisterPolicy.kv', encoding='utf8') as f:
            Builder.load_string(f.read())
        CPECafe.register_policy_page = RegisterPolicyPage()
        screen = Screen(name='RegisterPolicy')
        screen.add_widget(CPECafe.register_policy_page)
        CPECafe.screen_manager.add_widget(screen)

        self.progress_bar.text = f'Loading: Register Policy Screen...'
        self.progress = self.progress + 1
        self.progress_bar.value = (self.progress/self.progress_max)*100

        # setting page 
        with open(f'lib\\Setting.kv', encoding='utf8') as f:
            Builder.load_string(f.read())
        CPECafe.setting_page = SettingPage()
        screen = Screen(name='Setting')
        screen.add_widget(CPECafe.setting_page)
        CPECafe.screen_manager.add_widget(screen)

        self.progress_bar.text = f'Loading: Register Policy Screen...'
        self.progress = self.progress + 1
        self.progress_bar.value = (self.progress/self.progress_max)*100

        with open(f'lib\\Finish.kv', encoding='utf8') as f:
            Builder.load_string(f.read())
        CPECafe.finish_page = FinishPage()
        screen = Screen(name='Finish')
        screen.add_widget(CPECafe.finish_page)
        CPECafe.screen_manager.add_widget(screen)

        self.progress_bar.text = f'Loading: Finish Screen...'
        self.progress = self.progress + 1
        self.progress_bar.value = (self.progress/self.progress_max)*100

        CPECafe.screen_manager.current = 'Home'
        #CPECafe.screen_manager.current = 'Finish'
        #CPECafe.finish_page.start()

        CPECafe.tsc.monitor(4)


class HomePage(GridLayout):

    carousel = ObjectProperty(None)
    smartcard_text = ObjectProperty(None)
    smartcard_image = ObjectProperty(None)

    clock = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class SettingPage(GridLayout):
    
    carousel = ObjectProperty(None)
    smartcard_text = ObjectProperty(None)
    smartcard_image = ObjectProperty(None)

    clock = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    # def callback_home(self):   
    #     CPECafe.screen_manager.current = 'Home'
    #     CPECafe.screen_manager.transition = SlideTransition(direction='left')

    

class RegisterPolicyPage(GridLayout):

    registration_policy = ObjectProperty(None)

    account_type = None
    citizen = None
    campus = None
    code = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.snackbar = None

    def start(self, account_type, citizen, campus, code=None):
        
        self.tsc = SmartCardBehavior(
            self.name,
            card_insert_callback=None,
            card_remove_callback=None,
            card_reinsert_callback=None,
            card_remove_forever_callback=self.card_remove_forever_callback)

        self.account_type = account_type.lower()
        self.citizen = citizen
        self.campus = campus
        self.code = code

        #self.tsc.monitor(4, self.citizen)

        f = open("lib\\Policy.txt", "r", encoding="utf8")
        policy = f.read()
        self.ids.registration_policy.text = policy

        self.ids.account_policy_refuse.size_hint = [.8, None]
        self.ids.account_policy_accept.size_hint = [.8, None]

    def account_creation_not_accept_click_callback(self):
        Logger.info('RegisterPolicyPage: Not accept policy, then return to Home screen')
        CPECafe.tsc.reject()

    def account_creation_accept_click_callback(self):
        Logger.info('RegisterPolicyPage: Register a new Account and then open Set Password screen')

        self.snackbar_show(text=f'กรุณารอสักครู่ - กำลังสมัครบัญชีสมาชิกใหม่กับระบบจัดการข้อมูลและบริการอินเทอร์เน็ต')

        self.tsc = SmartCardBehavior(self)
        self.citizen = self.tsc.citizen
        # fail = False
        # print(self.citizen)
        #
        #
        # Insert data to database
        #
        #

        self.snackbar_hide()

        if self.citizen:
            Logger.info('RegisterPolicyPage: Open SetPassword screen')
            #self.snackbar_show('We are register your information as RMUTi internet account. Please wait...')

            CPECafe.screen_manager.transition = SlideTransition(direction='left')
            CPECafe.screen_manager.current = 'Finish'
            #CPECafe.tsc.smart_card_removable = False
            CPECafe.finish_page.start()
            #self.tsc.unmonitor()
            return

        CPECafe.tsc.dialog(
            title='เกิดข้อผิดพลาด...',
            size=('380dp', '180dp'),
            size_hint=(None, None),
            #text='The RMUTI Internet Accounting Service is down',
            text='ขออภัย.. เราไม่สามารถให้บริการได้',
            text_button_ok='OK')
        return

    def card_remove_forever_callback(self):
        if self.account_type != None:
            self.account_type_select.add_widget(self.ids.account_type_text)
        self.account_type = None

    def snackbar_show(self, text, duration=8):
        if self.snackbar:
            self.snackbar = None
        self.snackbar = Snackbar(text=text, duration=duration)
        self.snackbar.show()
        #Clock.schedule_once(self.snackbar_hide, wait)

    def snackbar_hide(self, instance=None):
        if self.snackbar:
            self.snackbar.hide()
            self.snackbar = None

class FinishPage(GridLayout):

    account_type = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.snackbar = None

    def start(self):
        
        self.tsc = SmartCardBehavior(
            self.name,
            card_insert_callback=None,
            card_remove_callback=None,
            card_reinsert_callback=None,
            card_remove_forever_callback=self.card_remove_forever_callback,
            card_removable=True)
        
        #self.tsc.monitor(4)

    def card_remove_forever_callback(self):
        pass

    def snackbar_show(self, text, duration=8):
        if self.snackbar:
            self.snackbar = None
        self.snackbar = Snackbar(text=text, duration=duration)
        self.snackbar.show()
        #Clock.schedule_once(self.snackbar_hide, wait)

    def snackbar_hide(self, instance=None):
        if self.snackbar:
            self.snackbar.hide()
            self.snackbar = None


class CPECafeApp(MDApp):

    title = 'CPE Cafe WiFi'
    #title = 'ระบบบริการบัญชีสมาชิกอินเทอร์เน็ต มทร.อีสาน'

    font_thin = APP_FOLDER_NAME+'\\lib\\resources\\SukhumvitSet-Text.ttf'
    font_regular = APP_FOLDER_NAME+'\\lib\\resources\\SukhumvitSet-Medium.ttf'
    font_bold = APP_FOLDER_NAME+'\\lib\\resources\\SukhumvitSet-SemiBold.ttf'
    font_name = 'SukhumvitSet'

    smart_card = None

    citizen = None
    account = None
    menu = None

    def __init__(self, **kwargs):
        
        LabelBase.register(
            name='SukhumvitSet',
            fn_regular=APP_FOLDER_NAME+'\\lib\\resources\\SukhumvitSet-Medium.ttf',
            fn_italic=APP_FOLDER_NAME+'\\lib\\resources\\SukhumvitSet-Medium.ttf',
            fn_bold=APP_FOLDER_NAME+'\\lib\\resources\\SukhumvitSet-Bold.ttf',
            fn_bolditalic=APP_FOLDER_NAME+'\\lib\\resources\\SukhumvitSet-Bold.ttf')
        theme_font_styles.append('SukhumvitSet')
        self.theme_cls.font_styles['SukhumvitSet'] = [
            'SukhumvitSet',
            16,
            False,
            0.15,]

        self.theme_cls.primary_palette = 'Blue'

        super().__init__(**kwargs)
        #self.dialog_change_theme = None
        #self.toolbar = None
        self.snackbar = None

    def build(self):
        self.screen_manager = ScreenManager(transition=NoTransition())

        self.tsc = SmartCardBehavior(
            'Home',
            reader_added_callback=self.smart_card_reader_added_callback,
            reader_removed_callback=self.smart_card_reader_removed_callback,
            card_insert_callback=self.smart_card_inserted_callback,
            #card_remove_callback=self.smart_card_remove_callback,
            card_reinsert_callback=None,
            card_remove_forever_callback=None)

        with open(f'lib\\Loading.kv', encoding='utf8') as f:
            Builder.load_string(f.read())
        self.loading_page = LoadingPage()
        screen = Screen(name='Loading')
        screen.on_enter = self.loading_page.load_pages
        screen.add_widget(self.loading_page)
        self.screen_manager.add_widget(screen)

        return self.screen_manager

    def smart_card_reader_added_callback(self, added_readers):
        #CPECafe.home_page.smartcard_text.text = f'Citizen Card was inserted'
        #CPECafe.home_page.smartcard_text.text = f'มีการต่ออุปกรณ์อ่านบัตรประจำตัวประชาชน'
        Logger.info('CPECafeApp: SmartCard reader added')

    def smart_card_reader_removed_callback(self, removed_readers):
        #CPECafe.home_page.smartcard_text.text = f'Citizen Card was inserted'
        #CPECafe.home_page.smartcard_text.text = f'มีการถอดอุปกรณ์อ่านบัตรประจำตัวประชาชน'
        Logger.info('CPECafeApp: SmartCard reader removed')

    def smart_card_inserted_callback(self, **kwargs):
        Logger.info('CPECafeApp: SmartCard inserted')
        #CPECafe.home_page.smartcard_text.text = f'Citizen Card was inserted'
        CPECafe.home_page.smartcard_text.text = f'มีการเสียบบัตรประจำตัวประชาชน'
        #CPECafe.home_page.smartcard_image.source = f'lib\\resources\\card_in_use_512px.png'        

        # Read Citizen ID
        if self.tsc.citizen != None:

            self.citizen = self.tsc.citizen

            #self.citizen = '0409000609020'

            self.account = None
            Logger.info('CPECafeApp: Open Register screen')
            CPECafe.screen_manager.transition = SlideTransition(direction='left')
            CPECafe.screen_manager.current = 'RegisterPolicy'
            self.tsc.smart_card_removable = True
            CPECafe.register_policy_page.start()

            return

    def smart_card_remove_callback(self, **kwargs):
        Logger.info('CPECafeApp: SmartCard removed')

    def snackbar_show(self, text, duration=8):
        if self.snackbar:
            self.snackbar = None
        self.snackbar = Snackbar(text=text, duration=duration)
        self.snackbar.show()

    def snackbar_hide(self, instance=None):
        if self.snackbar:
            self.snackbar.hide()
            self.snackbar = None

    def callback_earthe(self):
        print('callback_earthe')
        menu = 1
        return menu

    def callback_wifi(self):
        hostname = "www.google.com"
        response = os.system("ping " + hostname)
        # and then check the response...
        if response == 0:
            pingstatus = "Network Active"
        else:
            pingstatus = "Network Error"

        return pingstatus
    
    # def check_ping():
    #     hostname = "taylor"
    #     response = os.system("ping -c 1 " + hostname)
    #     # and then check the response...
    #     if response == 0:
    #         pingstatus = "Network Active"
    #     else:
    #         pingstatus = "Network Error"

    #     return pingstatus

    def callback_key(self):
        print('callback_key')
        menu = 3
        return menu

    def callback_setting(self):
        print('callback_setting')
        menu = 4
        CPECafe.screen_manager.transition = SlideTransition(direction='left')
        CPECafe.screen_manager.current = 'Setting'
        return menu
    
    def callback_login(self,menu):
        pass

    # setting screen menu

    def callback_home(self):   
        CPECafe.screen_manager.current = 'Home'
        CPECafe.screen_manager.transition = SlideTransition(direction='right')

    def callback_save(self):
        # save to database
        print('callback_save')

if __name__ == '__main__':
    CPECafe = CPECafeApp()
    CPECafe.run()
