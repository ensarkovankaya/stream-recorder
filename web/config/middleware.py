from django.utils import translation


class LocaleMiddleware(object):
    """
    This is a very simple middleware that parses a request
    and decides what translation object to install in the current
    thread context. This allows pages to be dynamically
    translated to the language the user desires (if the language
    is available, of course).
    """

    def process_request(self, request):
        language = translation.get_language_from_request(request)
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        translation.deactivate()
        return response

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language_code = "tr"
        translation.activate(language_code)
        response = self.get_response(request)
        return response
