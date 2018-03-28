# -*- coding: utf-8 -*-

import logging
import types
import urllib
import hashlib
from collections import OrderedDict

try:
    import json
except ImportError:
    try:
        import json
    except ImportError:
        from django.utils import json

from milky.error import RTMSystemError, RTMRequestError, \
        ERRCODE_NETWORK, ERRCODE_JSON, ERRCODE_UNKNOWN
from milky import request

API_URL = 'http://api.rememberthemilk.com/services/rest/'
AUTH_URL = 'http://www.rememberthemilk.com/services/auth/'

CHARSET = 'utf-8'
DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
PERMS_READ = u'read'
PERMS_WRITE = u'write'
PERMS_DELETE = u'delete'

# For parametars
_PALAM_TRUE = 1
_PARAM_FALSE = 0

# has_due_time parametars for task due
HAS_DUE_TIME = _PALAM_TRUE
HAS_NOT_DUE_TIME = _PARAM_FALSE

# For priority
PRIORITY_HIGH = 1
PRIORITY_MEDIUM = 2
PRIORITY_LOW = 3
PRIORITY_NONE = 0

# Recurrence frequencies
FREQ_YEARLY = u'YEARLY'
FREQ_MONTHLY = u'MONTHLY'
FREQ_WEEKLY = u'WEEKLY'
FREQ_DAILY = u'DAILY'

class API(object):
    """rememberthemilk.com API.
    
    Args:
        api_key - RTM API key.
        shared_secret - RTM shared secret.
        perms - Access permissions (Default: "read")
        token - token for granted access (Optional)

    Permissions:
        read - gives the ability to read task, contact, group and list 
            details and contents.
        write - gives the ability to add and modify task, contact, 
            group and list details and contents (also allows you to read).
        delete - gives the ability to delete tasks, contacts, groups 
            and lists (also allows you to read and write).
    """

    def __init__(self, api_key, shared_secret, perms=PERMS_READ, 
            frob=None, token=None, user_agent=None):

        """Create RTM instance."""

        self.api_key = api_key
        self.shared_secret = shared_secret
        self.perms = perms
        self.frob = frob
        self.token = token
        self.user_agent = user_agent

        if user_agent:
            class RTMURLopener(urllib.FancyURLopener):
                version = user_agent
            urllib._urlopener = RTMURLopener()

        for prefix, methods in request.METHODS.items():
            setattr(self, prefix, Request(self, prefix, methods))

    def __sign(self, params):
        """Generate sign with MD5 hash."""

        sortedkeys = sorted(params, key=str.lower)
        pairs=""
        for keyItem in sortedkeys:
            pairs=pairs+"{}{}".format(keyItem,params[keyItem])        
        pairs = pairs.encode(CHARSET)
        return hashlib.md5(self.shared_secret.encode(CHARSET)+pairs).hexdigest()

    def __call(self, url, params):
        if params:
            url = '%s?%s' % (url, urllib.parse.urlencode(OrderedDict(
                [(k, v.encode(CHARSET) if type(v) is str else v) \
                        for (k, v) in params.items()])))
        logging.debug(url)
        return urllib.request.urlopen(url)

    def get(self, method, auth_required, model_cls, **params):
        params = OrderedDict(params)
        params['method'] = method
        params['api_key'] = self.api_key
        params['format'] = 'json'
        if auth_required:
            params['auth_token'] = self.get_token()
        params['api_sig'] = self.__sign(params)

        try:
            row = self.__call(API_URL, params).read()
        except Exception as e:
            raise RTMSystemError('Cannot connect RTM.', ERRCODE_NETWORK)
        logging.debug(row)

        try:
            rsp = OrderedDict(json.loads(row))['rsp']
        except Exception as e:
            raise RTMSystemError('Cannot parse response.', ERRCODE_JSON)

        if rsp['stat'] != 'ok':
            if rsp['err'] \
                    and rsp['err']['msg'] \
                    and rsp['err']['code']:
                logging.debug(row)
                msg = rsp['err']['msg'].encode(CHARSET)
                code = int(rsp['err']['code'])
                logging.warn("%s (%d)" % (msg, code))
                raise RTMRequestError(msg, code)
            else:
                raise RTMSystemError('An unknown error has occurred.', ERRCODE_UNKNOWN)

        return model_cls._parse(rsp)

    def get_frob(self):
        if not self.frob:
            self.frob = self.auth.getFrob()
        return self.frob

    def get_auth_url(self):
        params = OrderedDict([
                ('api_key', self.api_key),
                ('perms', self.perms),
                ('frob', self.get_frob()), ])
        params['api_sig'] = self.__sign(params)
        return '%s?%s' % (AUTH_URL, urllib.parse.urlencode(params))

    def get_token(self):
        if not self.token:
            auth = self.auth.getToken(frob=self.get_frob())
            self.token = auth.token
        return self.token

class Request(object):
    """API request creator."""

    def __init__(self, rtm, prefix, methods):
        self.rtm = rtm
        self.prefix = prefix
        self.methods = methods

    def __getattr__(self, attr):
        if attr not in self.methods:
            raise AttributeError('No such attribute %s' % attr)
        auth_required, required_args, optional_args, \
                model_cls = self.methods[attr]
        if self.prefix == 'tasksnotes':
            method = 'rtm.tasks.notes.%s' % attr
        else:
            method = 'rtm.%s.%s' % (self.prefix, attr)

        return lambda **params: self.__call(
                method, auth_required, required_args, optional_args, 
                model_cls, **params)

    def __call(self, method, auth_required, required_args, optional_args, 
            model_cls, **params):

        for required_arg in required_args:
            if required_arg not in params:
                raise TypeError('Missing required parameter %s' % required_arg)

        return self.rtm.get(method, auth_required, model_cls, **params)

def test_rtm():
    from milky import test_configs as configs
    rtm = API(configs.RTM_API_KEY, configs.RTM_SHARED_SECRET, PERMS_DELETE)
    print (rtm.test.echo())

if __name__ == '__main__':
    test_rtm()

