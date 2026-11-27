class Transport:
    """What a client sends requests through: post(path, body, headers) -> response dict."""

    def post(self, path, body, headers):
        raise NotImplementedError
