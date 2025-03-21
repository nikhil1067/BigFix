import requests
from requests.auth import HTTPBasicAuth

class APIRequest:
    def __init__(self, base_url=None, proxy_url=None, proxy_username=None, proxy_password=None):
        """
        Initialize the APIRequest class with optional base URL and proxy configuration.

        :param base_url: Base URL for the API (default is None).
        :param proxy_url: Proxy URL (default is None).
        :param proxy_username: Username for the proxy (default is None).
        :param proxy_password: Password for the proxy (default is None).
        """
        self.base_url = base_url
        self.proxies = None
        
        if proxy_url:
            self.proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
            if proxy_username and proxy_password:
                # Add proxy authentication
                self.proxies["http"] = f"http://{proxy_username}:{proxy_password}@{proxy_url}"
                self.proxies["https"] = f"https://{proxy_username}:{proxy_password}@{proxy_url}"

    def request(self, method, endpoint=None, username=None, password=None, headers=None, params=None, data=None, json=None, verify=True):
        """
        Make an API request using the specified method.

        :param method: HTTP method (GET, POST, PUT, DELETE, etc.).
        :param endpoint: API endpoint (can be a full URL or a relative path).
        :param username: Username for HTTP Basic Authentication (default is None).
        :param password: Password for HTTP Basic Authentication (default is None).
        :param headers: Request headers (default is None).
        :param params: Query parameters for GET requests (default is None).
        :param data: Form data for POST/PUT requests (default is None).
        :param json: JSON payload for POST/PUT requests (default is None).
        :return: Response object.
        """
        if endpoint:
            url = f"{self.base_url}{endpoint}"
        else:
            url = f"{self.base_url}"

        # Set up authentication
        auth = HTTPBasicAuth(username, password) if username and password else None

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json,
                auth=auth,
                proxies=self.proxies,
                verify=verify
            )
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"An error occurred during the request: {e}")