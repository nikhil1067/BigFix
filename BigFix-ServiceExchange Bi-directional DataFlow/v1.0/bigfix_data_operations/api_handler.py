import requests
import xml.etree.ElementTree as ET
from utils.api_operations_template import APIRequest
from logger import logger
import urllib3
import json

urllib3.disable_warnings()

class BigFixAPIHandler:
    def __init__(self, config_path, base_url, username, password, proxy_url, proxy_username, proxy_password, verify, bigfix_properties_sx_to_bf):
        self.config_path = config_path
        self.base_url = base_url
        self.username = username
        self.password = password
        self.verify = verify
        self.properties = bigfix_properties_sx_to_bf
        self.APIRequestHandler = APIRequest(base_url=base_url, proxy_url=proxy_url, proxy_username=proxy_username, proxy_password=proxy_password)

    def get_property_value(self, api_data, property_path):
        """
        Extracts a specific property from API response.
        Supports dot notation for nested JSON parsing.
        """
        keys = property_path.split('.')  # Split nested fields
        value = api_data

        try:
            for key in keys:
                if isinstance(value, str):  # Convert JSON string to dictionary or list
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        return value  # Return as-is if not JSON
                if isinstance(value, list):  # If it's a list, pick the first element
                    value = value[0] if value else None
                if value is None:
                    return None  # Return None if key not found

                value = value.get(key)  # Fetch nested key

            return value
        except Exception as e:
            print(f"Error extracting {property_path}: {e}")
            return None

    def get_computer_data(self):
        """Fetch detailed computer data from BigFix, mapping backend fields to display names."""
        try:
            computer_ids = self.get_computer_ids()
            logger.info(f"Fetched {len(computer_ids)} computer IDs from BigFix.")
            computer_details = []

            for computer_id in computer_ids:
                details = self.get_computer_details(computer_id)
                print(details)                
                logger.info(details)
                computer_details.append(details)
            print(computer_details)
            return computer_details
        except Exception as e:
            logger.error(f"Error fetching BigFix computer data: {e}")
            return None
    
    def get_computer_ids(self):
        """Fetch all computer IDs from BigFix."""
        endpoint = "/api/computers"
        try:
            logger.info(f"Fetching computer IDs from BigFix: {endpoint}")
            response = self.APIRequestHandler.request(method="GET", endpoint=endpoint, username=self.username, password=self.password, verify=self.verify)
            response.raise_for_status()
            return self.parse_ids_from_xml(response.text)
        except requests.RequestException as e:
            logger.error(f"Error fetching computer IDs from BigFix: {e}")
            return []
        
    def validate_connection(self):
        """Validating Connection to BigFix."""
        endpoint = "/api/query"
        params = {"relevance": "number of bes computers"}
        try:
            logger.info(f"Validating Connection to BigFix: {endpoint}")
            response = self.APIRequestHandler.request(method="GET", endpoint=endpoint, params=params, username=self.username, password=self.password, verify=self.verify)
            response.raise_for_status()
            return response.status_code
        except requests.RequestException as e:
            logger.error(f"Error fetching computer IDs from BigFix: {e}")
            return []

    def get_computer_details(self, computer_id):
        """Fetch detailed information for a single computer by ID."""
        endpoint = f"/api/computer/{computer_id}"
        try:
            logger.info(f"Fetching details for computer ID: {computer_id}")
            response = self.APIRequestHandler.request(method="GET", endpoint=endpoint, username=self.username, password=self.password, verify=self.verify)
            response.raise_for_status()
            return self.parse_details_from_xml(response.text)
        except requests.RequestException as e:
            logger.error(f"Error fetching details for computer ID {computer_id}: {e}")
            return {prop: None for prop in self.properties}

    def parse_ids_from_xml(self, xml_data):
        """Parse computer IDs from BigFix XML response."""
        root = ET.fromstring(xml_data)
        return [comp_id.text for comp_id in root.findall(".//ID")]

    def parse_details_from_xml(self, xml_data):
        """Parse detailed information of a computer from BigFix XML response."""
        root = ET.fromstring(xml_data)
        parsed_details = {}

        # Gather all properties
        for prop in root.findall(".//Property"):
            name = prop.get("Name")
            value = prop.text
            if name in parsed_details:
                if isinstance(parsed_details[name], list):
                    parsed_details[name].append(value)
                else:
                    parsed_details[name] = [parsed_details[name], value]
            else:
                parsed_details[name] = value

        # Convert properties with multiple values into comma-separated strings
        for key, value in parsed_details.items():
            if isinstance(value, list):
                parsed_details[key] = ", ".join(value)

        return parsed_details