class ConnectError(Exception):
    """The request never reached the server."""


class ReadTimeout(Exception):
    """The request reached the server; the response did not come back."""


class HTTPError(Exception):
    def __init__(self, status, body=None):
        super().__init__(status)
        self.status, self.body = status, body
