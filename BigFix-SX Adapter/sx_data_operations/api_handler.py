import requests
import json
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
import xml.etree.ElementTree as ET
from utils.logger import logger
import urllib3
from utils.api_operations_template import APIRequest

urllib3.disable_warnings()

class SXAPIHandler:
    def __init__(self, config_path, record_limit, base_url, username, password):
        self.config_path = config_path
        self.sx_config = self.load_sx_config()
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json',
            'x-user-payload': self.sx_config.get('user_payload', '')
        }
        self.username = username
        self.password = password
        self.auth = (username, password)
        self.properties = self.sx_config['properties']
        self.record_limit = record_limit
        self.APIRequestHandler = APIRequest(base_url)

    def load_sx_config(self):
        """Parse the SX configuration from the XML file."""
        try:
            tree = ET.parse(self.config_path)
            root = tree.getroot()
            
            sx_config = {}
            sx_element = root.find('sx')
            
            # Properties
            properties = sx_element.find('properties')
            sx_config['properties'] = [
                prop.attrib['name'] for prop in properties.findall('property')
            ]

            # User payload
            user_payload = sx_element.find('user_payload')
            if user_payload is not None:
                sx_config['user_payload'] = user_payload.text.strip()

            return sx_config
        except Exception as e:
            logger.error(f"Failed to parse SX configuration: {e}")
            raise

    def get_computer_data(self):
        """Fetch all computer details from SX."""
        try:
            logger.info(f"Fetching all computer details from SX API.")

            # Initialize variables for pagination
            all_data = []
            current_page = 1
            limit = self.record_limit

            # Parse the base URL and query parameters
            params = {"purpose": "BigfixToCMDB-FetchCI", "client": "Bf_CMDB", "page" : 1, "limit" : limit}

            while True:
                # Update the query parameters for pagination
                params['page'] = [current_page]

                # Make the API request
                response = self.APIRequestHandler.request(method="GET", endpoint=None, params=params, username=self.username, password=self.password, headers=self.headers, verify=False)
                response.raise_for_status()

                # Parse the JSON response
                response_json = response.json()

                # Extract the data from the current page
                page_data = self.parse_computer_details(response_json)
                all_data.extend(page_data)

                # Extract metadata to handle pagination
                meta = response_json.get('meta', {})
                total_pages = meta.get('totalPageCount', 1)
                current_page = meta.get('currentPage', current_page)

                # Log progress
                logger.info(f"Fetched page {current_page}/{total_pages}.")

                # Check if we've fetched all pages
                if current_page >= total_pages:
                    break

                # Move to the next page
                current_page += 1

            logger.info(f"Fetched {len(all_data)} computer records from SX API.")
            return all_data
        except requests.RequestException as e:
            logger.error(f"Error fetching SX computer data: {e}")
            return None

    def parse_computer_details(self, response_json):
        """Parse all computer details from SX API response."""
        data = response_json.get('data', [])
        processed_data = []
        for computer in data:
            entry = {}
            for prop in self.properties:
                value = computer.get(prop, "")
                if isinstance(value, list):
                    entry[prop] = ", ".join(value)  # Convert lists to comma-separated strings
                else:
                    entry[prop] = value or ""  # Default to empty string if None
            
            processed_data.append(entry)
        return processed_data
    
    def post_computer_details(self, details):
        params = {"purpose": "Bigfix-IE-ToCMDB", "client": "Bf_CMDB"}
        payload = {
            "ciName": details["Computer Name"],
            "ipAddress": details["IP Address"],
            "macAddress": details["MAC Address"],
            "serialNumber": "",
            "description": "",
            "assetTag": " ",
            "class": "System",
            "status": "Requested",
            "subStatus": "Planned",
            "category": "Other",
            "subCategory": "Other",
            "type": "Asset",
            "businessCriticality": "High",
            "environment": "Qa",
            "dataset": "Golden",
            "companyName": "Hindustan Unilever Limited",
            "supportCompanyName": "Hindustan Unilever Limited",
            "supportGroup": "Testing Support Group",
            "technicalOwner": "HCLT_BreakfixManager@hclt.com",
            "businessOwner": "HCLT_BreakfixManager@hclt.com",
            "assignedTo": "HCLT_BreakfixManager@hclt.com",
            "location": "Noida_126",
            "isExternal": "false",
            "clientCINumber": details["Computer Name"],
            "clientName": "HCL"
        }
        response_post = self.APIRequestHandler.request(method="POST", endpoint=None, data=payload, params=params, username=self.username, password=self.password, headers=self.headers, verify=False)

        # Log and check response
        if response_post.status_code == 200:
            logger.info(f"Successfully posted data of computer {details['Computer Name']} from BigFix to ServiceExchange.")
        else:
            logger.error(f"Failed to post data of computer {details['Computer Name']} from BigFix to ServiceExchange. Status Code: {response_post.status_code}, Response: {response_post.text}")
        return response_post