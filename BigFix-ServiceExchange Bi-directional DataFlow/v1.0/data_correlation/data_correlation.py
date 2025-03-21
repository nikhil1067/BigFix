import xml.etree.ElementTree as ET
import json

class DataCorrelation:
    """Class to handle data correlation between BigFix and SX data."""

    @staticmethod
    def normalize_ip_addresses(ip_data):
        """Normalize IP addresses into a list format."""
        if isinstance(ip_data, str):
            return [ip.strip() for ip in ip_data.split(",") if ip.strip()]
        elif isinstance(ip_data, list):
            return [ip.strip() for ip in ip_data if ip.strip()]
        return []
    
    @staticmethod
    def parse_identity_properties(xml_file):
        """
        Parse identity properties from the dataflowconfig.xml file.
        Extracts properties used for correlation with display names.
        """
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        identity_properties = {"bigfix": {}, "sx": {}}

        # Extract identity properties from the ServiceExchange adapter
        sx_adapter = root.find(".//sourceadapter")
        if sx_adapter is not None:
            for prop in sx_adapter.findall(".//identityproperty"):
                identity_properties["sx"][prop.attrib["displayname"]] = prop.attrib["propertyname"]

        # Extract identity properties from the BigFix adapter
        bf_adapter = root.find(".//targetadapter")
        if bf_adapter is not None:
            for prop in bf_adapter.findall(".//identityproperty"):
                identity_properties["bigfix"][prop.attrib["displayname"]] = prop.attrib["propertyname"]

        return identity_properties
    
    @staticmethod
    # Function to get nested property values
    def get_property_value(api_data, property_path):
        keys = property_path.split('.')
        value = api_data

        for key in keys:
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    return value

            if isinstance(value, list):
                value = next((item.get(key, None) for item in value if isinstance(item, dict)), None)

            if value is None:
                return None

            value = value.get(key, None)

        return value
    
    @staticmethod
    # Function to correlate BigFix and SX data
    def correlate(bigfix_data, sx_data, bigfix_properties, sx_properties, identity_properties):
        correlated_data = []
        sx_data_map = {}

        # Extract identity property keys in the given order
        bigfix_identities = list(identity_properties["bigfix"].keys())
        sx_identities = list(identity_properties["sx"].keys())

        # Debug: Print identity property mappings
        print(f"BigFix Identities: {bigfix_identities}")
        print(f"SX Identities: {sx_identities}")

        # Ensure both lists are of the same length
        if len(bigfix_identities) != len(sx_identities):
            raise ValueError("Mismatch in number of identity properties between BigFix and SX.")

        # Create a mapping of SX identity properties to corresponding data
        for sx_item in sx_data:
            sx_identity_values = set()
            print(sx_item)
            for i in range(len(sx_identities)):
                print(sx_identities[i])
                sx_value = DataCorrelation.get_property_value(sx_item, sx_identities[i])  # Use nested key extraction
                print(f"Extracted SX Value [{sx_identities[i]}]: {sx_value}")  # Debug print

                if sx_value:
                    sx_identity_values.add(str(sx_value).lower().strip())

            if sx_identity_values:
                print(f"Storing SX Identity Key: {sx_identity_values}")  # Debug print
                sx_data_map[frozenset(sx_identity_values)] = sx_item  # Store SX items using tuple keys

        # Correlate BigFix data
        for bf_item in bigfix_data:
            correlated_item = {}

            # Extract BigFix identity values as a set
            bf_identity_values = set()

            for i in range(len(bigfix_identities)):
                bf_value = DataCorrelation.get_property_value(bf_item, bigfix_identities[i])  # Use nested key extraction
                print(f"Extracted BF Value [{bigfix_identities[i]}]: {bf_value}")  # Debug print

                if bf_value:
                    bf_identity_values.add(str(bf_value).lower().strip())

            print(f"Checking BigFix Identity Key: {bf_identity_values}")  # Debug print

            # Check for any matching values in SX identity sets
            matched_sx_item = None
            for sx_identity_values in sx_data_map.keys():
                if bf_identity_values & sx_identity_values:  # Check intersection
                    matched_sx_item = sx_data_map[sx_identity_values]
                    print(f"Match Found! {bf_identity_values} <=> {sx_identity_values}")  # Debug print
                    break  # Stop at the first match

            if matched_sx_item:
                # Add dynamically defined BigFix properties using display names
                for display_name, property_name in bigfix_properties.items():
                    correlated_item[display_name] = bf_item.get(display_name, "")

                # Add dynamically defined SX properties using display names (excluding identity properties)
                for display_name, property_name in sx_properties.items():
                    if display_name not in identity_properties["bigfix"]:  # Avoid duplicate identity properties
                        correlated_item[display_name] = DataCorrelation.get_property_value(matched_sx_item, display_name)

                correlated_data.append(correlated_item)

        print(f"Final Correlated Data: {correlated_data}")  # Debug print
        return correlated_data