import requests, time, re
from vkapi.TOTP import generateTOTP
import vkapi.VkAPI
import getpass


DEFAULT_API_VERSION = '5.80'


class AuthorizationException(Exception):
    def __init__(self, message, response):
        self.message = message
        self.response = response

    def __str__(self):
        return self.message


class UnauthorizedException(Exception):
    pass


class Credentials:
    def __init__(self, login, password, cid, scope='140492246', secret_key='', v=DEFAULT_API_VERSION):
        self.login = login
        self.password = password
        self.cid = cid
        self.scope = scope
        self.secret_key = secret_key
        self.v = v

    @staticmethod
    def fromstdin():
        cid = input('cid: ')
        login = input('Login: ')
        password = getpass.getpass('Password: ')
        scope = input('Scope: ') or '140492246'    # require all permissions in case of empty scope
        secret_key = input('Secret key: ')
        v = input('API version: ') or DEFAULT_API_VERSION
        return Credentials(login, password, cid, scope, secret_key, v)


class ImplicitFlow:
    def log(self, message, end='\n'):
        print('[VkAuth] ' + message, end=end)

    def authorize(self, credentials):
        try:
            udata = self.get_implicit_user_token(credentials.login,
                                                 credentials.password,
                                                 credentials.cid,
                                                 credentials.scope,
                                                 credentials.secret_key,
                                                 credentials.v)

            api = vkapi.VkAPI.VkAPI(credentials.cid, udata[0], time.time(), float(udata[1]), udata[2], credentials.v)
            return api
        except AuthorizationException as e:
            self.log('Authorization failed.')
            self.log(e.response.text)

    def get_implicit_user_token(self, login, password, cid, scope, secret_key, v):
        s = requests.session()
        params = {'client_id': cid,
                  'display': 'popup',
                  'redirect_uri': 'https://oauth.vk.com/blank.html',
                  'scope': scope,
                  'response_type': 'token',
                  'v': v}
        response = s.get('https://oauth.vk.com/authorize', params=params)
        P = r'<input type="hidden" name="(.+?)" value="(.+?)".*?>'
        data = dict(re.findall(P, response.text, flags=re.S))
        data['act'] = 'login'
        data['soft'] = '1'
        data['email'] = login
        data['pass'] = password
        response = s.post('https://login.vk.com/', data=data)
        if 'oauth.vk.com/authorize' in response.url:
            raise AuthorizationException('Wrong login or password...', response)
        response = self.is_authcheck_required(s, response, secret_key)
        response = self.is_grant_needed(s, response)
        udata = self.parse_token(response.url)
        if udata:
            self.log('Success!')
            return (udata.group(1), udata.group(2), udata.group(3))
        raise AuthorizationException('Unknown error occurred...', response)

    def parse_token(self, url):
        P = r'https://oauth.vk.com/blank\.html#access_token=(\w+?)&expires_in=(\w*?)&user_id=(\w+)'
        data = re.search(P, url, flags=re.S)
        return data

    def is_grant_needed(self, s, resp):
        P = r'<form method="post" action=".*?(act=grant_access.*?)".*?>'
        grant_action = re.search(P, resp.text, flags=re.S)
        if grant_action:
            self.log('Granting permissions to the application...')
            grant_url = 'https://login.vk.com/?' + grant_action.group(1)
            return s.post(grant_url)
        return resp

    def is_authcheck_required(self, s, resp, secret_key, i=0):
        P = r'<form method="post" action=".*?act=authcheck_code\&hash=(.+?)".*?>'
        _hash = re.search(P, resp.text, flags=re.S)
        if _hash:
            if i > 0:
                self.log('Authcheck failed. Trying again...')
            if i == 3:
                raise AuthorizationException('Authcheck code is wrong. Check your secret key...', resp)
            code = {'code': self.getTOTP(secret_key)}
            code['act'] = 'authcheck_code'
            code['hash'] = _hash.group(1)
            self.log('Sending authcheck code...')
            confirm_response = s.post('https://m.vk.com/login', data=code)
            response = self.is_captcha_required(s, confirm_response, secret_key)
            response = self.is_authcheck_required(s, response, secret_key, i+1)
            return response
        return resp

    def is_captcha_required(self, s, resp, secret_key):
        P_CAPTCHA = r'<input type="hidden" name="captcha_sid" value="(.+?)">'
        P_PARAMS = r'<input type="hidden" name="(.+?)" value="(.*?)">'
        P_ACTION = r'<form action="(.*?)" method="post">'
        captcha_sid = re.search(P_CAPTCHA, resp.text, flags=re.S)
        while captcha_sid:
            self.log('Captcha is required:')
            action = re.search(P_ACTION, resp.text, flags=re.S).group(1)
            params = re.findall(P_PARAMS, resp.text, flags=re.S)
            data = dict(params)
            self.log('https://m.vk.com/captcha.php?sid={}'.format(captcha_sid.group(1)))
            captcha = input('[VkAuth] Input captcha: ')
            data['captcha_key'] = captcha
            if 'code' in data:
                data['code'] = self.getTOTP(secret_key)
            resp = s.post('https://m.vk.com' + action, data=data)
            captcha_sid = re.search(P_CAPTCHA, resp.text, flags=re.S)
        return resp

    def getTOTP(self, secret_key):
        if not secret_key:
            return input('[VkAuth] Enter your second factor: ')
        T = int(time.time() / 30)
        return generateTOTP(secret_key, format(T, 'x'), 6)

