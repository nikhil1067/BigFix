import xml.etree.ElementTree as ET

class ConfigWriter:
    def __init__(self, xml_file):
        """
        Initialize the ConfigWriter with an XML file.
        """
        self.xml_file = xml_file

    def write_username(self, section, username):
        """
        Write the username to the specified section in the XML file as plain text.
        """
        # Parse the XML file
        tree = ET.parse(self.xml_file)
        root = tree.getroot()

        # Find the section to update
        for elem in root.findall(f".//{section}/credentials"):
            username_elem = elem.find("username")

            if username_elem is not None:
                username_elem.text = username
                break

        # Write the updated XML back to the file
        tree.write(self.xml_file, encoding="utf-8", xml_declaration=True)

    def retrieve_username(self, section):
        """
        Retrieve the username from the specified section in the XML file.
        Returns the username as a string, or None if not found.
        """
        # Parse the XML file
        tree = ET.parse(self.xml_file)
        root = tree.getroot()

        # Find the section to read
        for elem in root.findall(f".//{section}/credentials"):
            username_elem = elem.find("username")

            if username_elem is not None:
                return username_elem.text

        return None