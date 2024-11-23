class NgenicException(Exception):
    """Base exception class"""
    pass

class ApiException(NgenicException):
    """Exception from ngenic API"""

class ClientException(NgenicException):
    """Exception from library"""

    def __init__(self, msg, cause=None):
        super(ClientException, self).__init__(self, msg)
        self.msg = msg