import vkapi.VkAuth
import time, json, requests


class VkAPI:
    API_URL = 'https://api.vk.com/method/'
    
    def __init__(self, cid, access_token, token_time, expire_time, uid, api_version):
        self.cid = cid
        self.authorized = not not access_token  #TODO: this should be a function!! not a variable
        self.access_token = access_token
        self.token_time = token_time
        self.expire_time = expire_time
        self.uid = uid
        self.api_version = api_version

    def log(self, message, end='\n'):
        print('[VkAPI] ' + str(message), end=end)

    def serialize(self):
        data = {'cid': self.cid,
                'access_token': self.access_token,
                'token_time': self.token_time,
                'expire_time': self.expire_time,
                'uid': self.uid,
                'api_version': self.api_version}
        return json.dumps(data)

    @staticmethod
    def deserialize(data):
        data = json.loads(data)
        api = VkAPI(data['cid'],
                    data['access_token'],
                    data['token_time'],
                    data['expire_time'],
                    data['uid'],
                    data['api_version'])
        return api

    def is_token_expired(self):
        if not self.authorized:
            return False
        if self.expire_time == 0:
            return False
        if (self.expire_time + self.token_time) - time.time() <= 0:
            return True
        return False

    def send_request(self, method, params={}, access_token=True):
        if access_token:
            if not self.authorized:
                raise vkapi.VkAuth.UnauthorizedException('You are not authorized...')
            if self.is_token_expired():
                raise vkapi.VkAuth.UnauthorizedException('Your access token has expired...')
            params['access_token'] = self.access_token
            params['v'] = self.api_version
        url = self.API_URL + method

        #making post http request
        error = True
        while error:
            try:
                response = requests.post(url, data = params).text
                #self.log('RESPONSE: {}'.format(response))
                response = json.loads(response)
                error = False
            except Exception as e:
                self.log(e)
                self.log('Try again?', end=' ')
                if input():
                    continue
                else:
                    return

        while 'error' in response:
            error = response['error']
            code = error['error_code']
            if code == 14:
                response['captcha_sid'] = error['captcha_sid']
                self.log('Captcha is required...')
                self.log(error['captcha_img'])
                self.log('Input captcha:', end=' ')
                response['captcha_key'] = input()
                response = json.loads(requests.post(url, data = params).text)
            elif code == 18 or code == 15:
                self.log('Error {} occurred: "{}"'.format(code, error['error_msg']))
                return
            elif code == 6 or code == 10:
                self.log('Error {} occurred: "{}"'.format(code, error['error_msg']))
                self.log('Waiting a second...')
                time.sleep(1)
                response = json.loads(requests.post(url, data = params).text)
            else:
                self.log('Unexpected error occurred...')
                self.log(error)
                self.log('Try again?', end=' ')
                if input():
                    response = json.loads(requests.post(url, data = params).text)
                else:
                    return
        return response['response']

    def users_get(self, uids, fields, access_token = True):
        params = {'user_ids': uids, 'fields': fields}
        return self.send_request('users.get', params, access_token)

    def users_getFollowers(self, uid, fields = '', access_token = True):
        params = {'user_id': uid, 'fields': fields, 'count': 1000}
        return self.send_request('users.getFollowers', params, access_token)

    def friends_get(self, uid, fields = '', access_token = True):
        params = {'user_id': uid, 'fields': fields}
        return self.send_request('friends.get', params, access_token)

    def photos_getAll(self, uid, extended = 0, access_token = True):
        params = {'owner_id': uid, 'extended': extended, 'count': 200}
        photos = self.send_request('photos.getAll', params, access_token)
        if photos == None:
            return []
        photos_list = photos['items']
        count = photos['count']
        params['offset'] = 200
        while count > params['offset']:
            photos_i = self.send_request('photos.getAll', params, access_token)
            photos_list += photos_i['items']
            params['offset'] += 200
        return photos_list

    def photos_getUserPhotos(self, uid, extended = 0, access_token = True):
        params = {'user_id': uid, 'extended': extended, 'count': 1000}
        uphotos = self.send_request('photos.getUserPhotos', params, access_token)
        if uphotos == None:
            return []
        uphotos_list = uphotos['items']
        count = uphotos['count']
        params['offset'] = 1000
        while count > params['offset']:
            uphotos_i = self.send_request('photos.getUserPhotos', params, access_token)
            uphotos_list += uphotos_i['items']
            params['offset'] += 1000
        return uphotos_list

    def groups_get(self, uid, extended = 0, access_token = True):
        params = {'user_id': uid, 'extended': extended}
        groups = self.send_request('groups.get', params, access_token)
        return groups['items']

    def wall_get(self, uid, extended = 0, access_token = True):
        params = {'owner_id': uid, 'extended': extended, 'count': 100}
        resp = self.send_request('wall.get', params, access_token)
        if extended:
            groups = resp['groups']
            profiles = resp['profiles']
            wall = resp['wall']
            count = wall['count']
            wall = wall['items']
            params['offset'] = 100
            while count > params['offset']:
                resp = self.send_request('wall.get', params, access_token)
                groups += resp['groups']
                profiles += resp['profiles']
                wall += resp['wall']['items']
                params['offset'] += 100
            return {'groups': groups, 'profiles': profiles, 'wall': wall}
        else:
            return resp

