import requests


class Proxy:
    def __init__(self, raw_proxy):
        self.ip = ''
        self.port = ''
        self.username = ''
        self.password = ''
        self.one_line_proxy = ''
        self.start_data = ''
        self.requests = ''
        self.load(raw_proxy)

    def load(self, proxy):
        self.start_data = proxy
        self.ip, self.port, self.username, self.password = self.start_data.split(':')
        self.one_line_proxy = f'{self.username}:{self.password}@{self.ip}:{self.port}'
        self.requests = {'http': 'socks5h://' + self.one_line_proxy, 'https': 'socks5h://' + self.one_line_proxy}

    def is_work(self):
        try:
            ip = requests.get('https://api.my-ip.io/ip', proxies=self.requests, timeout=2).text
            if ip != self.ip:
                return False
            return True
        except:
            return False

    def id(self):
        return f'{self.ip.replace(".", "")}{self.port}'
