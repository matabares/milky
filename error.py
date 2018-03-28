# -*- coding: utf-8 -*-

ERRCODE_UNKNOWN = -999
ERRCODE_NETWORK = -10
ERRCODE_JSON = -20
ERRCODE_LOGIN_FAILED = 98

class MilkyError(Exception):
    """Milky exception"""

    def __init__(self, msg, no, response=None):
        super(MilkyError, self).__init__(msg)
        self.msg = msg
        self.no = int(no)
        self.response = response

    def __str__(self):
        return '%s (%d)' % (self.msg, self.no)

# API error for the system.
class RTMSystemError(MilkyError): pass
# API error for the user parameters.
class RTMRequestError(MilkyError): pass

