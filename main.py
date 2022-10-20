from typing import Union

import requests
import random
import string
import time

import twocaptcha.solver

from Proxy import Proxy
import nickname_generator
# from python_rucaptcha.enums import ReCaptchaEnm
# from python_rucaptcha.ReCaptcha import ReCaptcha
from python_rucaptcha.enums import FunCaptchaEnm
from python_rucaptcha.FunCaptcha import FunCaptcha
from pprint import pprint
from threading import Thread
from twocaptcha import TwoCaptcha


class Autoreg:
    def __init__(self):
        self.count = 10
        self.done = 0
        self.threads_count = 1
        self.threads = []
        self.rucaptcha_token = '3f7baa9a88b5082a40874354f6f57efe'
        self.arkose_public_key = 'E5554D43-23CC-1982-971D-6A2262A2CA24'
        self.done_filename = 'done.txt'
        self.mail_domain = '@gmail.com'
        self.proxies = []
        self.proxies_list = "https://proxy.webshare.io/proxy/list/download/vbgozgdszluszseyjlttwynrsjzlvxnrqpohopmc/-/socks/username/direct/"
        self.need_stop = False

    def load_proxies(self) -> None:
        self.proxies = requests.get(self.proxies_list).text.splitlines()

    def start(self):
        while True:
            for thread_id, cur_thread in enumerate(self.threads):
                if not cur_thread.is_alive():
                    cur_thread.join()
                    del self.threads[thread_id]
            if len(self.threads) < self.threads_count and self.count > (self.done + len(self.threads)):
                if self.need_stop:
                    time.sleep(1)
                    continue
                need_to_create = self.threads_count - len(self.threads)
                if need_to_create + self.done + len(self.threads) >= self.count:
                    need_to_create = self.count - (self.done + len(self.threads))
                for i in range(need_to_create):
                    asdf = Thread(target=self.register_account, args=(random.choice(self.proxies),))
                    asdf.daemon = True
                    asdf.start()
                    self.threads.append(asdf)
            if not self.threads:
                print("All tasks done")
                return True
            time.sleep(1)

    def register_account(self, proxy):
        proxy = Proxy(proxy)
        nickname = nickname_generator.generate()
        if not self.check_proxy_nickname(proxy, nickname):
            print('Bad proxy')
            return
        arkose_token = self.get_recaptcha_token()
        if not arkose_token:
            print("Bad captcha")
            return
        email, password = self.get_random_email(), self.get_random_string(18, True)
        resp = self.send_register_request(email, password, arkose_token['result']['code'], nickname, proxy)
        if not resp:
            if 'error_code' in resp.json():
                if resp.json()['error_code'] == 1000:
                    print("Bad captcha")
                    arkose_token['solver'].report(arkose_token['result']['captchaId'], False)
                else:
                    print(resp.json()['error_description'])
            else:
                print("Error with creating account, response: ", resp.text, resp.status_code)
            return False
        resp = resp.json()
        try:
            if 'access_token' not in resp:
                print("Unexpended gql error:", resp)
        except Exception as error:
            print("Exception with ", resp, error)
            return False
        arkose_token['solver'].report(arkose_token['result']['captchaId'], True)
        token = resp['access_token']
        acc_string = f'{nickname}:{password}:{token}'
        print(f'Account {self.done + 1} created ({acc_string})')
        with open(self.done_filename, 'a') as done_file:
            done_file.write(f'{acc_string}\n')
        self.done += 1
        return True

    def check_proxy_nickname(self, proxy, nickname):
        try:
            var = requests.post(
                'https://gql.twitch.tv/gql',
                json={
                    "operationName": "UsernameValidator_User",
                    "variables": {
                        "username": nickname
                    },
                    "extensions": {
                        "persistedQuery": {
                            "version": 1,
                            "sha256Hash": "fd1085cf8350e309b725cf8ca91cd90cac03909a3edeeedbd0872ac912f3d660"
                        }
                    }
                },
                headers={
                    'Client-ID': 'kd1unb4b3q4t58fwlpcbzcbnm76a8fp'
                },
                proxies=proxy.requests,
                timeout=15,
            ).json()
            return var['data']['isUsernameAvailable']
        except Exception as error:
            print("Exception with parsing username availability:", error)
            return False

    def send_register_request(self, email, password, arkose_token, nickname, proxy):
        # cap_token = arkose_token.split('|')[0]
        # cap_token += '|r=eu-west-1|metabgclr=transparent|guitextcolor=%23000000|metaiconclr=%23757575|meta=3|lang=en|pk=E5554D43-23CC-1982-971D-6A2262A2CA24|at=40|atp=2|cdn_url=https%3A%2F%2Fclient-api.arkoselabs.com%2Fcdn%2Ffc|lurl=https%3A%2F%2Faudio-eu-west-1.arkoselabs.com|surl=https%3A%2F%2Fclient-api.arkoselabs.com'
        try:
            return requests.post(
                'https://passport.twitch.tv/register',
                json={
                    "username": nickname,
                    "password": password,
                    "email": email,
                    "birthday": {
                        "day": random.randint(1, 27),
                        "month": random.randint(1, 12),
                        "year": random.randint(1950, 2000)
                    },
                    "client_id": "kd1unb4b3q4t58fwlpcbzcbnm76a8fp",
                    "include_verification_code": True,
                    "arkose": {"token": arkose_token},
                },
                headers={
                },
                proxies=proxy.requests
            )
        except Exception as error:
            print('Error with sending request for register:', error)
            return False

    def get_recaptcha_token(self) -> Union[str, bool]:
        print("Waiting for recaptcha")
        config = {
            'server': 'rucaptcha.com',
            'apiKey': self.rucaptcha_token,
        }
        solver = TwoCaptcha(**config)
        try:
            result = solver.funcaptcha(
                sitekey=self.arkose_public_key,
                url='https://passport.twitch.tv/register'
            )
        except twocaptcha.solver.TimeoutException:
            print("Too long solving captcha")
            return False
        except twocaptcha.solver.ApiException as api_exception:
            print('Exception with solving captcha, error:', str(api_exception))
            return False
        if result['code']:
            print("Recaptcha is done")
        else:
            print("No captcha token, response: ", result)
            if result['errorBody'] == 'ERROR_ZERO_BALANCE':
                print("Zero balance!")
                self.need_stop = True
        return {'solver': solver, 'result': result}

    def get_random_email(self) -> str:
        return self.get_random_string(random.randint(15, 30)) + self.mail_domain

    @staticmethod
    def get_random_string(length=32, use_uppercase=False) -> str:
        chars = string.ascii_lowercase + string.digits
        if use_uppercase:
            f = ''.join(random.choice(string.ascii_lowercase) for _ in range(int(length / 3)))
            f += ''.join(random.choice(string.ascii_uppercase) for _ in range(int(length / 3)))
            f += ''.join(random.choice(string.digits) for _ in range(int(length / 3)))
            return f
        return ''.join(random.choice(chars) for _ in range(length))


if __name__ == "__main__":
    test = Autoreg()
    test.rucaptcha_token = '50abbb7cbfe85b9ee319c9b74389c2f6'
    test.count = 100
    test.threads_count = 1
    test.load_proxies()
    test.start()
    # test.load_proxies()
    # for i in range(10):
    #     pprint(test.register_account(random.choice(test.proxies)))
