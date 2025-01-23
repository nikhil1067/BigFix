import requests
from requests.auth import HTTPBasicAuth
from utils.logger import logger
from utils.api_operations_template import APIRequest

class BigFixSiteHandler:
    def __init__(self, base_url, username, password, site_name):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.site_name = site_name
        self.APIRequestHandler = APIRequest(base_url)

    def get_site(self):
        """
        Send the API request to retrieve the site.
        """
        endpoint = f"/api/site/custom/{self.site_name}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response = self.APIRequestHandler.request(method="GET", endpoint=endpoint, username=self.username, password=self.password, headers=headers, verify=False)

            if response.status_code == 200:
                logger.info(f"Custom BES Site '{self.site_name}' is available. Proceeding further!")
                return True
            else:
                logger.error(f"Custom BES Site '{self.site_name}' is not available. Terminating the dataflow!")
                return False
        except Exception as e:
            logger.error(f"Error occurred while retrieving site: {e}")
            return None