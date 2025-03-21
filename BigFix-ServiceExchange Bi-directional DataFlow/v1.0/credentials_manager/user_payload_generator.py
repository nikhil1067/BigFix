import requests

class APIClient:
    """
    A unified API client that handles OAuth authentication and API requests.
    """
    def __init__(self, client_id, client_secret, token_url, base_url, username, password):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.base_url = base_url
        self.username = username
        self.password = password
        self.access_token = None

    def authenticate(self):
        """
        Authenticates the user and retrieves an OAuth token.
        """
        payload = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password
        }
        try:
            response = requests.post(self.token_url, data=payload, auth=(self.client_id, self.client_secret))
            response.raise_for_status()  # Raise an error for bad responses
            token_info = response.json()
            self.access_token = token_info.get("access_token")
            return self.access_token
        except requests.exceptions.RequestException as e:
            print(f"Error getting OAuth token: {e}")
            return None

    def make_request(self, endpoint):
        """
        Makes an authenticated GET request. If no token is available, it will authenticate first.
        """
        if not self.access_token:
            print("No access token found. Authenticating...")
            self.authenticate()

        if not self.access_token:
            print("Authentication failed. Cannot make request.")
            return None

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Bearer {self.access_token}',
        }
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json().get("x-user-payload")
        except requests.exceptions.RequestException as e:
            print(f"Error making API request: {e}")
            return None