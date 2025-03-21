import requests
from requests.auth import HTTPBasicAuth
from datetime import date, datetime
import xml.etree.ElementTree as ET
from logger import logger
from utils.api_operations_template import APIRequest

class BigFixAnalysisHandler:
    def __init__(self, base_url, username, password, site_name, proxy_url, proxy_username, proxy_password, hash_value, verify):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.site_name = site_name
        self.hash_value = hash_value
        self.verify = verify
        self.APIRequestHandler = APIRequest(base_url=base_url, proxy_url=proxy_url, proxy_username=proxy_username, proxy_password=proxy_password)

    def get_properties(self, property_names):
        """
        Gather property details dynamically based on user inputs for names and file path.
        Returns a list of properties with names and relevance expressions.
        """
        properties = []
        for index, name in enumerate(property_names):
            name = name.strip()
            relevance = (
                f'concatenation "," of tuple string item {index} of tuple string of substrings separated by "," of lines of file whose (name of it starts with "CMDBData-{self.hash_value}") of folder "mailboxsite" of data folder of client | "not set"'
            )
            properties.append({"Name": name, "Relevance": relevance})
        return properties

    def generate_analysis_payload(self, name, description, properties):
        """
        Generate XML payload for creating a BigFix analysis.
        """
        # Get current date and time in UTC
        current_time = datetime.utcnow()
        formatted_time = current_time.strftime("%d %b %Y %H:%M:%S +0000")

        analysis_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<BES xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="BES.xsd">
    <Analysis>
        <Title>{name}</Title>
        <Description><![CDATA[{description}]]></Description>
        <Relevance>exists file whose (name of it starts with "CMDBData-{self.hash_value}") of folder "mailboxsite" of data folder of client</Relevance>
        <Source>Internal</Source>
        <SourceReleaseDate>{date.today()}</SourceReleaseDate>
        <MIMEField>
          <Name>x-fixlet-modification-time</Name>
          <Value>{formatted_time}</Value>
        </MIMEField>
        <Domain>BESC</Domain>
    """
        for i, prop in enumerate(properties, start=1):
            analysis_template += f"""
        <Property Name="{prop['Name']}" ID="{i}">{prop['Relevance']}</Property>"""
        analysis_template += """
    </Analysis>
</BES>
        """
        return analysis_template.strip()

    def post_analysis(self, payload):
        """
        Send the API request to create the analysis.
        """
        endpoint = f"/api/analyses/custom/{self.site_name}"
        headers = {"Content-Type": "application/xml"}
        
        try:
            response = self.APIRequestHandler.request(method="POST", endpoint=endpoint, username=self.username, password=self.password, headers=headers, data=payload, verify=self.verify)

            if response.status_code == 200:
                logger.info("Analysis created successfully!")
            else:
                logger.error(f"Failed to create analysis. Status Code: {response.status_code}")
        except Exception as e:
            logger.error(f"Error occurred while creating analysis: {e}")

    def put_analysis(self, analysis_id, payload):
        """
        Send the API request to create the analysis.
        """
        endpoint = f"/api/analysis/custom/{self.site_name}/{analysis_id}"
        headers = {"Content-Type": "application/xml"}
        
        try:
            response = self.APIRequestHandler.request(method="PUT", endpoint=endpoint, data=payload, username=self.username, password=self.password, headers=headers, verify=self.verify)

            if response.status_code == 200:
                logger.info("Analysis created successfully!")
            else:
                logger.error(f"Failed to create analysis. Status Code: {response.status_code}")
        except Exception as e:
            logger.error(f"Error occurred while creating analysis: {e}")

    def get_analysis_id(self):
        """
        Send the API request to retrieve the analysis ID.
        """
        endpoint = f"/api/analyses/custom/{self.site_name}"
        headers={"Content-Type": "application/x-www-form-urlencoded"}
        
        try:
            response = self.APIRequestHandler.request(method="GET", endpoint=endpoint, username=self.username, password=self.password, headers=headers, verify=self.verify)

            if response.status_code == 200:
                try:
                    root = ET.fromstring(response.text)
                    analysis_id = root.find(".//ID").text
                    logger.info("Analysis ID retrieved successfully!")
                    return analysis_id
                except ET.ParseError as e:
                    logger.error(f"Error parsing XML: {e}")
                    return None
            else:
                logger.error(f"Failed to retrieve analysis ID. Status Code: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error occurred while retrieving analysis ID: {e}")
            return None