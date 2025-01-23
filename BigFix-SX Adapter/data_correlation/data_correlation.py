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
    def correlate(bigfix_data, sx_data, bigfix_properties, sx_properties):
        """Correlate data based on IP Address and fallback to MAC Address."""
        correlated_data = []
        sx_data_map = {}

        # Map SX properties
        sx_ip_property = sx_properties.get("IP_ADDRESS", "IP Address")
        sx_mac_property = sx_properties.get("MAC_ADDRESS", "MAC Address")

        # Prepare SX data map for efficient lookup
        for sx_item in sx_data:
            sx_ips = DataCorrelation.normalize_ip_addresses(sx_item.get(sx_ip_property, ""))
            sx_mac = sx_item.get(sx_mac_property, "")
            sx_data_map[(tuple(sx_ips), sx_mac)] = sx_item

        # Map BigFix properties
        bf_ip_property = bigfix_properties.get("IP Address", "IP Address")
        bf_mac_property = bigfix_properties.get("MAC Address", "MAC Address")

        # Correlate BigFix data
        for bf_item in bigfix_data:
            correlated_item = {}
            bf_ips = DataCorrelation.normalize_ip_addresses(bf_item.get(bf_ip_property, ""))
            bf_mac = bf_item.get(bf_mac_property, "")
            matched = False

            # IP address correlation
            for sx_ips, sx_mac in sx_data_map:
                if any(ip in sx_ips for ip in bf_ips):
                    sx_item = sx_data_map[(sx_ips, sx_mac)]
                    # Add all dynamically defined BigFix properties
                    for dynamic_key, dynamic_property in bigfix_properties.items():
                        correlated_item[dynamic_property] = bf_item.get(dynamic_property, "")

                    # Add all dynamically defined SX properties
                    for dynamic_key, dynamic_property in sx_properties.items():
                        if dynamic_key not in ["IP_ADDRESS", "MAC_ADDRESS"]:
                            correlated_item[dynamic_property] = sx_item.get(dynamic_property, "")
                    correlated_data.append(correlated_item)
                    matched = True
                    break

            # Fallback to MAC address correlation
            if not matched:
                for sx_ips, sx_mac in sx_data_map:
                    if bf_mac == sx_mac:
                        sx_item = sx_data_map[(sx_ips, sx_mac)]
                        # Add all dynamically defined BigFix properties
                        for dynamic_key, dynamic_property in bigfix_properties.items():
                            correlated_item[dynamic_property] = bf_item.get(dynamic_property, "")

                        # Add all dynamically defined SX properties
                        for dynamic_key, dynamic_property in sx_properties.items():
                            if dynamic_key not in ["IP_ADDRESS", "MAC_ADDRESS"]:
                                correlated_item[dynamic_property] = sx_item.get(dynamic_property, "")

                        correlated_data.append(correlated_item)
                        break

        return correlated_data