import requests
import xml.etree.ElementTree as ET
from utils.api_operations_template import APIRequest
from utils.logger import logger
import urllib3

urllib3.disable_warnings()

class BigFixAPIHandler:
    def __init__(self, config_path, base_url, username, password):
        self.config_path = config_path
        self.bigfix_config = self.load_bigfix_config()
        self.base_url = base_url
        self.username = username
        self.password = password
        self.properties = self.bigfix_config['properties']
        self.APIRequestHandler = APIRequest(base_url)

    def load_bigfix_config(self):
        """Parse the BigFix configuration from the XML file."""
        try:
            tree = ET.parse(self.config_path)
            root = tree.getroot()

            bigfix_config = {}
            bigfix_element = root.find('bigfix')

            # Properties
            properties = bigfix_element.find('properties')
            bigfix_config['properties'] = [
                prop.attrib['name'] for prop in properties.findall('property')
            ]

            return bigfix_config
        except Exception as e:
            logger.error(f"Failed to parse BigFix configuration: {e}")
            raise

    def get_computer_data(self):
        """Fetch detailed computer data from BigFix."""
        try:
            computer_ids = self.get_computer_ids()
            logger.info(f"Fetched {len(computer_ids)} computer IDs from BigFix.")
            computer_details = []
            for computer_id in computer_ids:
                details = self.get_computer_details(computer_id)
                computer_record = {**{prop: details.get(prop, None) for prop in self.properties}}
                computer_details.append(computer_record)
            return computer_details
        except Exception as e:
            logger.error(f"Error fetching BigFix computer data: {e}")
            return None

    def get_computer_ids(self):
        """Fetch all computer IDs from BigFix."""
        endpoint = "/api/computers"
        try:
            logger.info(f"Fetching computer IDs from BigFix: {endpoint}")
            response = self.APIRequestHandler.request(method="GET", endpoint=endpoint, username=self.username, password=self.password, verify=False)
            response.raise_for_status()
            return self.parse_ids_from_xml(response.text)
        except requests.RequestException as e:
            logger.error(f"Error fetching computer IDs from BigFix: {e}")
            return []

    def get_computer_details(self, computer_id):
        """Fetch detailed information for a single computer by ID."""
        endpoint = f"/api/computer/{computer_id}"
        try:
            logger.info(f"Fetching details for computer ID: {computer_id}")
            response = self.APIRequestHandler.request(method="GET", endpoint=endpoint, username=self.username, password=self.password, verify=False)
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
        properties = {}

        # Gather all properties
        for prop in root.findall(".//Property"):
            name = prop.get("Name")
            value = prop.text
            if name in properties:
                if isinstance(properties[name], list):
                    properties[name].append(value)
                else:
                    properties[name] = [properties[name], value]
            else:
                properties[name] = value

        # Convert properties with multiple values into comma-separated strings
        for key, value in properties.items():
            if isinstance(value, list):
                properties[key] = ", ".join(value)

        # Extract the required properties
        parsed_details = {prop: properties.get(prop, None) for prop in self.properties}
        return parsed_details