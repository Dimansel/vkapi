# Python VKAPI SDK

This simple tool allows one to use VK API comfortably via implemented authorization routine and abstraction layer for methods usage in a form of a class

## Usage examples
```python
from vkapi import VkAPI, VkAuth

# this will ask user to input
# login, password, application id, required permissions, secret key (2-FA) and API version
# last three could have their default values '140492246', '' and '5.80' respectively if left unspecified
creds = VkAuth.Credentials.fromstdin()

# alternatively you could provide all data directly to the Credentials constructor:
# creds = VkAuth.Credentials(login, password, cid, scope, secret_key, v)

# now create an instance of authorization flow
# currently Implicit Flow is the only implemented authorization flow
flow = VkAuth.ImplicitFlow()

# and finally invoke authorization using created credentials
# in the process user could be asked to input captcha or second factor in case of 2-FA (only if their's secret key was not provided)
api = flow.authorize(creds)

# if all is okay then we can call VK API methods
# this will return the user's friends sorted in the order as seen in "My Friends" section
# with link to a 50x50 photo for each friend
my_friends = api.send_request('friends.get', {'order': 'hints', 'fields': 'photo_50'})

# it is also possible to serialize api object to a JSON string and save it somewhere
token = api.serialize()

# and then deserialize that string to a VkAPI object again
api = VkAPI.VkAPI.deserialize(token)
```
