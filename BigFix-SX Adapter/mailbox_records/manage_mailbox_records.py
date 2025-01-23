import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
from utils.logger import logger

class MailboxManager:
    def __init__(self, base_url, username, password, hash_value):
        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, password)
        self.hash_value = hash_value

    def get_mailbox_files(self, computer_id):
        """
        Fetch all mailbox files for the given computer ID.
        """
        url = f"{self.base_url}/api/mailbox/{computer_id}"
        try:
            response = requests.get(url, auth=self.auth, verify=False)
            response.raise_for_status()
            logger.info("Successfully fetched mailbox files.")
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching mailbox files: {e}")
            return None

    def parse_cmdb_files(self, xml_data):
        """
        Parse XML data to extract IDs of files starting with 'CMDBData-hashvalue'.
        """
        cmdb_file_ids = []
        try:
            root = ET.fromstring(xml_data)
            for file in root.findall("ComputerMailboxFile"):
                name = file.find("Name").text
                file_id = file.find("ID").text
                if name.startswith(f"CMDBData-{self.hash_value}"):
                    cmdb_file_ids.append(file_id)
            logger.info(f"Parsed XML and found {len(cmdb_file_ids)} 'CMDBData' files.")
        except ET.ParseError as e:
            logger.error(f"Error parsing XML: {e}")
        return cmdb_file_ids

    def delete_file(self, file_id, computer_id):
        """
        Delete a specific file by its ID.
        """
        url = f"{self.base_url}/api/mailbox/{computer_id}/{file_id}"
        try:
            response = requests.delete(url, auth=self.auth, verify=False)
            if response.status_code == 200:
                logger.info(f"Successfully deleted file with ID {file_id}.")
            else:
                logger.warning(f"Failed to delete file with ID {file_id}: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            logger.error(f"Error deleting file with ID {file_id}: {e}")

    def process_and_delete_cmdb_files(self, computer_id):
        """
        Fetch all mailbox files, find 'CMDB' files, and delete them.
        """
        logger.info("Starting to process and delete 'CMDBData' files.")
        xml_data = self.get_mailbox_files(computer_id)
        if xml_data:
            cmdb_file_ids = self.parse_cmdb_files(xml_data)
            logger.info(f"Found 'CMDBData' files with IDs: {cmdb_file_ids}")
            for file_id in cmdb_file_ids:
                self.delete_file(file_id, computer_id)
        else:
            logger.error("No mailbox data to process.")

    def post_file(self, payload, computer_id):
        """Send a POST request with a dynamically generated filename."""
        filename = f"CMDBData-{self.hash_value}-{computer_id}"
        url = f"{self.base_url}/api/mailbox/{computer_id}"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Content-Disposition': f'name="FileContents";filename="{filename}"'
        }
        try:
            response = requests.post(
                url,
                headers=headers,
                data=payload,
                auth=self.auth,
                verify=False  # Disable SSL verification if needed
            )
            response.raise_for_status()  # Raise an exception for HTTP error responses
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during POST request to {url}: {e}")
            return None  # Return None to indicate an error