import requests
import json
import math
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
import xml.etree.ElementTree as ET
from logger import logger
import urllib3
from datetime import datetime, timezone
import isodate
from utils.api_operations_template import APIRequest

urllib3.disable_warnings()


class SXAPIHandler:
    def __init__(self, config_path, record_limit, base_url, username, password, proxy_url, proxy_username, proxy_password, verify, x_user_payload, sx_properties_sx_to_bf, delta):
        self.config_path = config_path
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json',
            'x-user-payload': x_user_payload
        }
        self.delta = delta
        self.username = username
        self.properties = sx_properties_sx_to_bf
        self.password = password
        self.auth = (username, password)
        self.record_limit = record_limit
        self.verify = verify
        self.APIRequestHandler = APIRequest(
            base_url=base_url,
            proxy_url=proxy_url,
            proxy_username=proxy_username,
            proxy_password=proxy_password
        )

    def get_computer_data(self):
        """Fetch all computer details from SX."""
        try:
            logger.info(f"Fetching all computer details from SX API.")

            # Initialize variables for pagination
            all_data = []
            current_page = 1
            limit = self.record_limit

            # Add technical attributes to headers
            self.headers['fetchattribute'] = 'true'
            
            # Parse the base URL and query parameters
            endpoint = "/cmdb/api/config_items/v2"
            params = {"page": 1, "limit": limit}

            # Add header for delta data
            if self.delta is not None:
                now = datetime.now(timezone.utc)
                delta = isodate.parse_duration(self.delta)
                start = now - delta
                # Format: MM-DD-YYYY
                start_str = start.strftime("%m-%d-%Y")
                end_str = now.strftime("%m-%d-%Y")
                # Create JSON string for header
                revamp_dict = {
                    "updated_at": f"{start_str}&{end_str}"
                }
                revamp_header = json.dumps(revamp_dict)  # Makes it a valid JSON string
                # Add it to headers
                self.headers['revamp'] = revamp_header

            while True:
                # Update the query parameters for pagination
                params['page'] = [current_page]

                # Make the API request
                response = self.APIRequestHandler.request(
                    method="GET",
                    endpoint=endpoint,
                    params=params,
                    username=self.username,
                    password=self.password,
                    headers=self.headers,
                    verify=self.verify
                )
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
            print(all_data)
            return all_data
        except requests.RequestException as e:
            logger.error(f"Error fetching SX computer data: {e}")
            return None

    def validate_connection(self):
        """Validating Connection to ServiceExchange."""
        params = {"page": 1, "limit": 10}
        try:
            logger.info("Validating Connection to Service Exchange")
            response = self.APIRequestHandler.request(
                method="GET",
                endpoint=None,
                params=params,
                username=self.username,
                password=self.password,
                verify=self.verify
            )
            response.raise_for_status()
            return response.status_code
        except requests.RequestException as e:
            logger.error(f"Error fetching computer IDs from BigFix: {e}")
            return []

    def get_property_value(self, api_data, property_path):
        """
        Extracts a specific property from the API response.
        Supports dot notation for nested JSON parsing, including recursive stringified JSON.
        """
        keys = property_path.split('.')
        value = api_data

        try:
            for key in keys:
                # Recursively parse stringified JSON if needed
                while isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        break  # Exit if it's just a regular string

                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None

                if value is None:
                    return None

            return value
        except Exception as e:
            logger.warning(f"Error extracting '{property_path}': {e}")
            return None
    
    def parse_computer_details(self, response_json):
        """Parse all computer details from API response using self.properties."""
        if self.delta is None:
            data = response_json.get('data', [])
        else:
            data = response_json.get('result', [])

        processed_data = []

        for computer in data:
            entry = {}
            for display_name, prop_info in self.properties.items():
                propertyname = prop_info.get("propertyname")
                proptype = prop_info.get("type")

                value = None

                if proptype == "general":
                    value = computer.get(propertyname)
                elif proptype == "technical":
                    for attr in computer.get("ATTRIBUTE", []):
                        if attr.get("attribute_name") == propertyname:
                            value = attr.get("attr_value")
                            break
                elif proptype == "custom":
                    for tag in computer.get("TAG", {}).get("tag_data", []):
                        if tag.get("tag_name") == propertyname:
                            value = tag.get("tag_value")
                            break

                # Flatten lists and ensure strings
                if isinstance(value, list):
                    entry[propertyname] = ", ".join(str(v) for v in value)
                else:
                    entry[propertyname] = str(value) if value is not None else ""

            logger.info(entry)
            print(entry)
            processed_data.append(entry)

        return processed_data

    def post_computer_details(self, device_data_list):
        record_limit_per_page = int(self.record_limit)
        total_records = len(device_data_list)
        total_pages = math.ceil(total_records / record_limit_per_page)

        for current_page in range(1, total_pages + 1):
            start_idx = (current_page - 1) * record_limit_per_page
            end_idx = min(start_idx + record_limit_per_page, total_records)

            payload = {
                'meta': {
                    'pushToCMDB': 'yes',
                    'currentCount': end_idx - start_idx,
                    'totalCount': total_records,
                    'currentPage': current_page
                },
                'data': device_data_list[start_idx:end_idx]
            }

            json_payload = json.dumps(payload, indent=4)
            print(json_payload)
            logger.info(json_payload)

            endpoint = '/cmdb/api/integration/bulk'
            response_post = self.APIRequestHandler.request(
                method='POST',
                endpoint=endpoint,
                data=json_payload,
                username=self.username,
                password=self.password,
                headers=self.headers,
                verify=self.verify
            )

            print(f'Page {current_page}/{total_pages} - Status Code: {response_post.status_code}')
            logger.info(f'Page {current_page}/{total_pages} - Status Code: {response_post.status_code}')
            print(response_post.text)
            logger.info(response_post.text)

        return