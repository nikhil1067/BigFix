import os
import xml.etree.ElementTree as ET
 
def load_config(config_file):
    """
    Load configuration from an XML file.
 
    Args:
        config_file (str): Path to the XML configuration file.
 
    Returns:
        dict: Configuration data as a nested dictionary.
    """
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file {config_file} not found.")
    try:
        tree = ET.parse(config_file)
        root = tree.getroot()
        def parse_element(element):
            """
            Recursively parse an XML element into a dictionary, including attributes.
 
            Args:
                element (xml.etree.ElementTree.Element): XML element.
 
            Returns:
                dict or str: Parsed data as a dictionary or string.
            """
            # Include attributes
            data = element.attrib.copy()
            children = list(element)
            if not children:  # If the element has no children, return its text.
                if element.text:
                    data['value'] = element.text.strip()
                return data if data else element.text.strip() if element.text else ""
            # Recursively parse children
            for child in children:
                parsed_child = parse_element(child)
                if child.tag not in data:  # First occurrence of the tag
                    data[child.tag] = parsed_child
                else:  # Handle multiple occurrences of the same tag
                    if not isinstance(data[child.tag], list):
                        data[child.tag] = [data[child.tag]]
                    data[child.tag].append(parsed_child)
            return data
 
        config = {root.tag: parse_element(root)}
        return config
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML format in configuration file {config_file}") from e
    except Exception as e:
        raise
