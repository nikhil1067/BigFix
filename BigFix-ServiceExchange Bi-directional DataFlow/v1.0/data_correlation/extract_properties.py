import xml.etree.ElementTree as ET

class PropertiesExtractor:
    """
    A class to extract properties from an XML configuration file, excluding specific fields.
    """
    def __init__(self, config_file):
        """
        Initialize the PropertiesExtractor with the given XML configuration file.

        :param config_file: Path to the XML configuration file.
        """
        self.config_file = config_file

    def extract_properties(self):
        """
        Extract and return the properties from the XML configuration file.
        Excludes 'IP_ADDRESS' and 'MAC_ADDRESS' from the ServiceXchange properties.

        :return: A dictionary containing BigFix and ServiceXchange properties.
        """
        bigfix_properties = []
        sx_properties = []

        try:
            # Parse the XML file
            tree = ET.parse(self.config_file)
            root = tree.getroot()

            # Extract BigFix properties
            bigfix_properties_node = root.find("bigfix/properties")
            if bigfix_properties_node is not None:
                bigfix_properties = [
                    prop.get("name") for prop in bigfix_properties_node.findall("property")
                    if prop.get("name")
                ]
            else:
                print("BigFix properties node not found.")

            # Extract ServiceXchange properties
            sx_properties_node = root.find("sx/properties")
            if sx_properties_node is not None:
                sx_properties = [
                    prop.get("name") for prop in sx_properties_node.findall("property")
                    if prop.get("name") not in ["IP_ADDRESS", "MAC_ADDRESS"]
                ]
            else:
                print("ServiceXchange properties node not found.")

        except ET.ParseError as e:
            print(f"Error parsing XML file: {e}")
        except FileNotFoundError:
            print(f"File not found: {self.config_file}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        # Return combined properties
        return bigfix_properties + sx_properties