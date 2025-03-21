import xml.etree.ElementTree as ET

class ConfigWriter:
    def __init__(self, xml_file):
        """
        Initialize the ConfigWriter with an XML file.
        """
        self.xml_file = xml_file

    def write_username(self, section, username, field):
        """
        Write the username to the specified section in the XML file as plain text.
        """
        # Parse the XML file
        tree = ET.parse(self.xml_file)
        root = tree.getroot()

        # Update username for the specified datasource
        datasource = root.find(f".//datasources/datasource[@datasourcename='{section}']")
        if datasource is not None:
            datasource.set(field, username)

        # Save the updated XML file
        tree.write(self.xml_file, encoding="utf-8", xml_declaration=True)

    def retrieve_username(self, section, field):
        """
        Retrieve the username from the specified section in the XML file.
        Returns the username as a string, or None if not found.
        """
        # Parse the XML file
        tree = ET.parse(self.xml_file)
        root = tree.getroot()

        # Update username for the specified datasource
        datasource = root.find(f".//datasources/datasource[@datasourcename='{section}']")
        if datasource is not None:
            datasource.get(field)

        # Save the updated XML file
        tree.write(self.xml_file, encoding="utf-8", xml_declaration=True)