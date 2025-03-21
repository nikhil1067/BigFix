def main(provide_credentials=False, init=False, provide_proxy_credentials=False, reset=False):
    from logger import logger
    from utils.generate_hash_value import CryptoServices
    from credentials_manager.crypto_services import CredentialManager
    from credentials_manager.config_writer import ConfigWriter
    from bigfix_data_operations.api_handler import BigFixAPIHandler
    from sx_data_operations.api_handler import SXAPIHandler
    from mailbox_records.manage_mailbox_records import MailboxManager
    from bigfix_data_operations.analysis_handler import BigFixAnalysisHandler
    from data_correlation.data_correlation import DataCorrelation
    from data_correlation.extract_properties import PropertiesExtractor
    from bigfix_data_operations.site_handler import BigFixSiteHandler
    from utils.manage_cache import CacheManager
    from credentials_manager.user_payload_generator import APIClient
    import getpass
    import json
    import csv
    import os
    import sys
    import xml.etree.ElementTree as ET
    from sys import exit

    # Load configuration
    exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    config_path = os.path.join(exe_dir, "DataFlowsConfig.xml")
    tree = ET.parse(config_path)
    root = tree.getroot()
    SETTINGS = {setting.get('key'): setting.get('value') for setting in root.findall(".//settings/setting")}
    logger.info(SETTINGS)
    print(SETTINGS)

    # Define file paths
    preview_records_path = os.path.join(exe_dir, "Preview_Records.csv")
    cache_path = os.path.join(exe_dir, "RecordsCache.dat")

    # Generate a unique hash
    crypto_services = CryptoServices()
    if reset:
        # Reset unique_hash when --reset flag is used
        new_hash = crypto_services.generate_unique_hash(config_path=config_path)
        print(f"Reset completed. New CMDB Hash: {new_hash}")
        # Delete RecordsCache.dat if it exists
        if os.path.exists(cache_path):
            os.remove(cache_path)
            print("Deleted RecordsCache.dat file.")
        return
    # Read unique_hash from XML, if empty, generate a new one
    unique_hash = root.get("uniquehash", "").strip()
    if not unique_hash:
        unique_hash = crypto_services.generate_unique_hash(config_path=config_path)
    print(f"Using CMDB Hash: {unique_hash}")
    
    # Check PREVIEW_ONLY setting
    preview_only = True if SETTINGS["preview_only"] == "True" else False

    # Initialize credentials management
    service = SETTINGS["locker_service_name"]
    credentials_manager = CredentialManager(service)
    config_writer = ConfigWriter(config_path)

    bigfix_config = root.find(".//datasources/datasource[@datasourcename='BigFixRestAPI']")
    logger.info(bigfix_config)
    print(bigfix_config)
    sx_config = root.find(".//datasources/datasource[@datasourcename='ServiceExchangeAPI']")
    logger.info(sx_config)
    print(sx_config)

    # Handle API credentials
    if provide_credentials:
        bigfix_username = input("Enter BigFix Master Operator Username: ")
        bigfix_password = getpass.getpass("Enter BigFix Master Operator Password: ")
        credentials_manager.add_credential(bigfix_username, bigfix_password)
        config_writer.write_username(section="BigFixRestAPI", field="username", username=bigfix_username)

        sx_username = input("Enter Service Exchange API Username: ")
        sx_password = getpass.getpass("Enter Service Exchange API Password: ")
        credentials_manager.add_credential(sx_username, sx_password)
        sx_client_id = input("Enter Service Exchange API Client ID: ")
        sx_client_secret = getpass.getpass("Enter Service Exchange API Client Secret: ")
        credentials_manager.add_credential(sx_client_id, sx_client_secret)
        config_writer.write_username(section="ServiceExchangeAPI", field="clientid", username=sx_client_id)
        config_writer.write_username(section="ServiceExchangeAPI", field="username", username=sx_username)
        return
    
    # Handle Proxy credentials
    if provide_proxy_credentials:
        bigfix_proxy_username = input("Enter BigFix Proxy Username: ")
        bigfix_proxy_password = getpass.getpass("Enter BigFix Proxy Password: ")
        credentials_manager.add_credential(bigfix_proxy_username, bigfix_proxy_password)
        config_writer.write_username(section="BigFixRestAPI", field="proxyusername", username=bigfix_proxy_username)

        sx_proxy_username = input("Enter Service Exchange Proxy Username: ")
        sx_proxy_password = getpass.getpass("Enter Service Exchange Proxy Password: ")
        credentials_manager.add_credential(sx_proxy_username, sx_proxy_password)
        config_writer.write_username(section="ServiceExchangeAPI", field="proxyusername", username=sx_proxy_username)
        return
    
    # List of dataflow names to extract properties for
    dataflow_names = [
        "Transfer Asset Data from ServiceExchange to Bigfix",
        "Transfer Asset Data from Bigfix to ServiceExchange"
    ]

    # Dictionary to store properties for each dataflow
    dataflows_properties = {}

    for dataflow_name in dataflow_names:
        dataflow = root.find(f".//dataflows/dataflow[@displayname='{dataflow_name}']")
        
        if dataflow is not None:
            properties_dict = {}
            for adapter in ["sourceadapter", "targetadapter"]:
                adapter_element = dataflow.find(adapter)
                if adapter_element is not None:
                    datasource_name = adapter_element.get("datasourcename")
                    device_properties = adapter_element.find("device_properties")
                    
                    if device_properties is not None:
                        properties = {prop.get("displayname"): prop.get("propertyname") for prop in device_properties.findall("property")}
                        identity_properties = {prop.get("displayname"): prop.get("propertyname") for prop in device_properties.findall("identityproperty")}
                        properties_dict[datasource_name] = {**properties, **identity_properties}  # Merge both dictionaries
            dataflows_properties[dataflow_name] = properties_dict
        else:
            dataflows_properties[dataflow_name] = None

    # Dataflow properties - ServiceExchange to BigFix
    bigfix_properties_sx_to_bf = dataflows_properties["Transfer Asset Data from ServiceExchange to Bigfix"]["BigFixRestAPI"] if dataflows_properties["Transfer Asset Data from ServiceExchange to Bigfix"] else None
    print(bigfix_properties_sx_to_bf)
    sx_properties_sx_to_bf = dataflows_properties["Transfer Asset Data from ServiceExchange to Bigfix"]["ServiceExchangeAPI"] if dataflows_properties["Transfer Asset Data from ServiceExchange to Bigfix"] else None
    print(sx_properties_sx_to_bf)

    # Dataflow properties - BigFix to ServiceExchange
    bigfix_properties_bf_to_sx = dataflows_properties["Transfer Asset Data from Bigfix to ServiceExchange"]["BigFixRestAPI"] if dataflows_properties["Transfer Asset Data from Bigfix to ServiceExchange"] else None
    print(bigfix_properties_bf_to_sx)
    sx_properties_bf_to_sx = dataflows_properties["Transfer Asset Data from Bigfix to ServiceExchange"]["ServiceExchangeAPI"] if dataflows_properties["Transfer Asset Data from Bigfix to ServiceExchange"] else None
    print(sx_properties_bf_to_sx)

    record_limit = SETTINGS["record_limit_per_page"]
    # Retrieve credentials and Initialize API Handlers
    bigfix_username = bigfix_config.get("username")
    bigfix_password = credentials_manager.retrieve_password(bigfix_username)
    bigfix_proxy_url = bigfix_config.get("proxyurl") if len(bigfix_config.get("proxyurl")) > 0 else None
    bigfix_ssl_verify = True if bigfix_config.get("verifycert") == "true" else False
    bigfix_connection = bigfix_config.get("connectionstring")
    bigfix_site_name = bigfix_config.get("site")
    if bigfix_proxy_url:
        bigfix_proxy_username = bigfix_config.get("proxyusername")
        bigfix_proxy_password = credentials_manager.retrieve_password(bigfix_proxy_username)
        bigfix_api = BigFixAPIHandler(config_path=config_path, base_url=bigfix_connection, username=bigfix_username, password=bigfix_password, proxy_url=bigfix_proxy_url, proxy_username=bigfix_proxy_username, proxy_password=bigfix_proxy_password, verify=bigfix_ssl_verify, bigfix_properties_sx_to_bf=bigfix_properties_sx_to_bf)
        bes_site = BigFixSiteHandler(base_url=bigfix_connection, username=bigfix_username, password=bigfix_password, site_name=bigfix_site_name, proxy_url=bigfix_proxy_url, proxy_username=bigfix_proxy_username, proxy_password=bigfix_proxy_password, verify=bigfix_ssl_verify)
        analysis_manager = BigFixAnalysisHandler(base_url=bigfix_connection, username=bigfix_username, password=bigfix_password, site_name=bigfix_site_name, hash_value=unique_hash, proxy_url=bigfix_proxy_url, proxy_username=bigfix_proxy_username, proxy_password=bigfix_proxy_password, verify=bigfix_ssl_verify)
    else:
        bigfix_api = BigFixAPIHandler(config_path=config_path, base_url=bigfix_connection, username=bigfix_username, password=bigfix_password, proxy_url=None, proxy_username=None, proxy_password=None, verify=bigfix_ssl_verify, bigfix_properties_sx_to_bf=bigfix_properties_sx_to_bf)
        bes_site = BigFixSiteHandler(base_url=bigfix_connection, username=bigfix_username, password=bigfix_password, site_name=bigfix_site_name, proxy_url=None, proxy_username=None, proxy_password=None, verify=bigfix_ssl_verify)
        analysis_manager = BigFixAnalysisHandler(base_url=bigfix_connection, username=bigfix_username, password=bigfix_password, site_name=bigfix_site_name, hash_value=unique_hash, proxy_url=None, proxy_username=None, proxy_password=None, verify=bigfix_ssl_verify)
    
    sx_username = sx_config.get("username")
    sx_password = credentials_manager.retrieve_password(sx_username)
    sx_proxy_url = sx_config.get("proxyurl") if len(sx_config.get("proxyurl")) > 0 else None
    sx_ssl_verify = True if sx_config.get("verifycert") == "true" else False
    sx_connection = sx_config.get("connectionstring")
    sx_client_id = sx_config.get("clientid")
    sx_client_secret = credentials_manager.retrieve_password(sx_client_id)
    sx_token_url = sx_config.get("tokenurl")
    sx_user_payload_api = APIClient(client_id=sx_client_id, client_secret=sx_client_secret, token_url=sx_token_url, base_url=sx_connection, username=sx_username, password=sx_password)
    sx_user_payload_api_endpoint = "fdn/xsmauth/authorize"
    sx_user_payload = sx_user_payload_api.make_request(sx_user_payload_api_endpoint)
    if sx_proxy_url:
        sx_proxy_username = sx_config.get("proxyusername")
        sx_proxy_password = credentials_manager.retrieve_password(sx_proxy_username)
        sx_api = SXAPIHandler(config_path=config_path, record_limit=record_limit, base_url=sx_connection, username=sx_username, password=sx_password, proxy_url=sx_proxy_url, proxy_username=sx_proxy_username, proxy_password=sx_proxy_password, verify=sx_ssl_verify, x_user_payload=sx_user_payload, sx_properties_sx_to_bf=sx_properties_sx_to_bf)
    else:
        sx_api = SXAPIHandler(config_path=config_path, record_limit=record_limit, base_url=sx_connection, username=sx_username, password=sx_password, proxy_url=None, proxy_username=None, proxy_password=None, verify=sx_ssl_verify, x_user_payload=sx_user_payload, sx_properties_sx_to_bf=sx_properties_sx_to_bf)

    # Handle init operations
    if init:
        bigfix_test_connection = bigfix_api.validate_connection()
        if bigfix_test_connection == 200:
            logger.info("BigFix Connection Validation Completed successfully!")
            print("BigFix Connection Validation Completed successfully!")
        else:
            logger.error("BigFix Connection Validation Failed!")
            print("BigFix Connection Validation Failed!")
        sx_test_connection = sx_api.validate_connection()
        if sx_test_connection == 200:
            logger.info("ServiceExchange Connection Validation Completed successfully!")
            print("ServiceExchange Connection Validation Completed successfully!")
        else:
            logger.error("ServiceExchange Connection Validation Failed!")
            print("ServiceExchange Connection Validation Failed!")
        return
    
    mailbox_manager = MailboxManager(bigfix_connection, bigfix_username, bigfix_password, unique_hash)
    properties = PropertiesExtractor(config_path)
    cache = CacheManager(cache_path)

    try:
        if not bes_site.get_site():
            logger.error("BigFix site does not exist.")
            exit(100)

        logger.info("Fetching data from BigFix...")
        bigfix_data = bigfix_api.get_computer_data() or []
        print(bigfix_data)
        
        # Parse DataFlow XML
        dataflow_root = (ET.parse(config_path)).getroot()
        
        ############# Processing DataFlow #############
        ############# Transfer Asset Data from Bigfix to ServiceExchange #############
        if dataflows_properties['Transfer Asset Data from Bigfix to ServiceExchange']:
            
            # Checks for new bigfix data
            if not bigfix_data:
                logger.error("BigFix Data not available to correlate/send to ServiceExchange.")
                exit(100)

            # Create mapping dictionaries
            bigfix_direct_mapping = {}  # For <property> and <identityproperty>
            bigfix_setting_mapping = {}  # For <setting>

            # Find the correct dataflow
            dataflow = dataflow_root.find(".//dataflow[@displayname='Transfer Asset Data from Bigfix to ServiceExchange']")
            if dataflow is None:
                logger.error("ERROR: DataFlow not found!")
                exit(100)

            source_adapter = dataflow.find(".//sourceadapter")
            target_adapter = dataflow.find(".//targetadapter")

            if source_adapter is None or target_adapter is None:
                logger.error("ERROR: Source or Target Adapter missing in DataFlow XML")
                exit()

            source_device_props = source_adapter.find(".//device_properties")
            target_device_props = target_adapter.find(".//device_properties")

            if source_device_props is None or target_device_props is None:
                logger.error("ERROR: device_properties missing in source or target adapter")
                exit()

            source_properties = list(source_device_props)
            target_properties = list(target_device_props)

            # Separate mapping creation
            for src_prop, tgt_prop in zip(source_properties, target_properties):
                src_name = src_prop.get("propertyname")
                tgt_name = tgt_prop.get("propertyname")
                tag = src_prop.tag.lower()

                if not src_name or not tgt_name:
                    continue

                if tag == "setting":
                    bigfix_setting_mapping[src_name] = tgt_name
                else:
                    bigfix_direct_mapping[src_name] = tgt_name

            # Debug: show mapping
            logger.info(f"Direct property mapping: {bigfix_direct_mapping}")
            logger.info(f"Client setting mapping: {bigfix_setting_mapping}")

            # Build BigFix to SX mapped data
            bigfix_data_bf_to_sx = []
            for device in bigfix_data:
                device_data = {}

                # Handle direct properties (property / identityproperty)
                for bf_key, sx_key in bigfix_direct_mapping.items():
                    value = device.get(bf_key)
                    if value is not None:
                        device_data[sx_key] = value

                # Handle settings from "Client Settings" string
                client_settings_str = device.get("Client Settings", "")
                settings_dict = {}

                if client_settings_str:
                    for setting in client_settings_str.split(","):
                        if "=" in setting:
                            k, v = setting.split("=", 1)
                            settings_dict[k.strip()] = v.strip()

                for bf_key, sx_key in bigfix_setting_mapping.items():
                    if bf_key in settings_dict:
                        device_data[sx_key] = settings_dict[bf_key]

                # Debug: show transformed device data
                print(device_data)
                bigfix_data_bf_to_sx.append(device_data)

            cached_bigfix_data = cache.load_from_cache('bf_to_sx') or []
            new_bigfix_data = [data for data in bigfix_data_bf_to_sx if data not in cached_bigfix_data]
            print(new_bigfix_data)
            
            cache.save_to_cache('bf_to_sx', bigfix_data_bf_to_sx)
            if not new_bigfix_data:
                logger.info("No new or changed data in BigFix for sending out to ServiceExchange.")
                print("No new or changed data in BigFix for sending out to ServiceExchange.")
             
            else:
                logger.info("Sending new BigFix data to Service Exchange...")
                print("Sending new BigFix data to Service Exchange...")

                if preview_only:
                    # **Determine indentation automatically**
                    indent_value = 4 if len(new_bigfix_data) <= 10 else 0

                    # Write JSON output to a file
                    output_filename = "Preview_Records_BFtoSX.json"
                    with open(output_filename, "w", encoding="utf-8") as json_file:
                        json.dump(new_bigfix_data, json_file, separators=(",", ":"))
                    
                    logger.info(f"JSON output saved to {output_filename} with indentation level {indent_value}.")
                    print(f"JSON output saved to {output_filename} with indentation level {indent_value}.")
                    return

                sx_api.post_computer_details(new_bigfix_data)
        
        ############# Transfer Asset Data from ServiceExchange to Bigfix #############
        if dataflows_properties['Transfer Asset Data from ServiceExchange to Bigfix']:
            correlated_data = None
            logger.info("Fetching data from SX...")
            sx_data = sx_api.get_computer_data() or []
            print(sx_data)
            
            if not bigfix_data or not sx_data:
                logger.error("Data not available to correlate.")
                exit(100)
            
            # Extract mappings from BigFix property names to display names
            bf_mappings = {}
            for dataflow in dataflow_root.findall(".//dataflow[@displayname='Transfer Asset Data from ServiceExchange to Bigfix']"):
                for targetadapter in dataflow.findall(".//targetadapter[@displayname='Bigfix Adapter']"):
                    for property_tag in targetadapter.findall(".//device_properties/*"):
                        display_name = property_tag.attrib["displayname"]
                        backend_name = property_tag.attrib["propertyname"]
                        bf_mappings[backend_name] = display_name

            # Convert BigFix data to the required format
            bigfix_data_sx_to_bf = []
            for entry in bigfix_data:
                formatted_entry = {bf_mappings[key]: value for key, value in entry.items() if key in bf_mappings}
                bigfix_data_sx_to_bf.append(formatted_entry)
            print(bigfix_data_sx_to_bf)
            
            # Extract mappings from SX property names to display names
            sx_mappings = {}
            for dataflow in dataflow_root.findall(".//dataflow[@displayname='Transfer Asset Data from ServiceExchange to Bigfix']"):
                for sourceadapter in dataflow.findall(".//sourceadapter[@displayname='ServiceExchange Adapter']"):
                    for property_tag in sourceadapter.findall(".//device_properties/*"):
                        display_name = property_tag.attrib["displayname"]
                        backend_name = property_tag.attrib["propertyname"]
                        sx_mappings[backend_name] = display_name

            # Convert ServiceExchange data to the required format
            sx_data_sx_to_bf = []
            for entry in sx_data:
                formatted_entry = {sx_mappings[key]: value for key, value in entry.items() if key in sx_mappings}
                sx_data_sx_to_bf.append(formatted_entry)
            print(sx_data_sx_to_bf)

            sx_to_bf_cache = cache.load_from_cache('sx_to_bf') or {}
			
            cached_bigfix_data = sx_to_bf_cache.get("bigfix_data", [])
            new_bigfix_data = [data for data in bigfix_data_sx_to_bf if data not in cached_bigfix_data]
            print(new_bigfix_data)

            cached_sx_data = sx_to_bf_cache.get("sx_data", [])
            new_sx_data = [data for data in sx_data_sx_to_bf if data not in cached_sx_data]
            print(new_sx_data)
			
            sx_to_bf_cache = {
                'bigfix_data': bigfix_data_sx_to_bf,
				'sx_data': sx_data_sx_to_bf
            }
            
            cache.save_to_cache('sx_to_bf', sx_to_bf_cache)
            
            if not new_bigfix_data or not new_sx_data:
                logger.info("No new or changed data in BigFix/ServiceExchange to process.")
                print("No new or changed data in BigFix/ServiceExchange to process.")
                exit(0)

            logger.info("Sending new Service Exchange data to BigFix data ...")
            identity_properties = DataCorrelation.parse_identity_properties(config_path)
            print(identity_properties)
            
            # Parse XML and extract mappings
            root = (ET.parse(config_path)).getroot()

            correlated_data = DataCorrelation.correlate(bigfix_data=new_bigfix_data, sx_data=new_sx_data, bigfix_properties=dataflows_properties['Transfer Asset Data from ServiceExchange to Bigfix']['BigFixRestAPI'], sx_properties=dataflows_properties['Transfer Asset Data from ServiceExchange to Bigfix']['ServiceExchangeAPI'], identity_properties=identity_properties)
        ####################################################
            print(correlated_data)
            
            if correlated_data:
                if preview_only:
                    # **Determine indentation automatically**
                    indent_value = 4 if len(correlated_data) <= 10 else 0

                    # Write JSON output to a file
                    output_filename = "Preview_Records_SXtoBF.json"
                    with open(output_filename, "w", encoding="utf-8") as json_file:
                        json.dump(correlated_data, json_file, separators=(",", ":"))
                    
                    logger.info(f"JSON output saved to {output_filename} with indentation level {indent_value}.")
                    print(f"JSON output saved to {output_filename} with indentation level {indent_value}.")
                    return
                else:
                    logger.info("Creating BigFix analysis...")
                    print("Creating BigFix analysis...")
                    analysis_name = "ServiceExchange Custom Properties"
                    analysis_description = "Analysis of correlated data between BigFix and ServiceExchange systems."
                    root = (ET.parse(config_path)).getroot()
                    property_names = [p.attrib["displayname"] for p in root.find(".//sourceadapter/device_properties").findall("*")] + [p.attrib["displayname"] for p in root.find(".//targetadapter/device_properties").findall("property")]
                    logger.info(f"Properties in Analysis: {property_names}")
                    print(property_names)
                    extracted_properties = analysis_manager.get_properties(property_names)
                    payload = analysis_manager.generate_analysis_payload(analysis_name, analysis_description, extracted_properties)

                    analysis_id = analysis_manager.get_analysis_id()
                    if analysis_id:
                        analysis_manager.put_analysis(analysis_id, payload)
                    else:
                        analysis_manager.post_analysis(payload)

                    for record in correlated_data:
                        payload = ",".join(str(record.get(prop, "")).replace(",", ";") for prop in property_names)
                        print(payload)
                        logger.info(payload)
                        bigfix_ID_propName = next((p.attrib["displayname"] for p in root.find(".//dataflow[@displayname='Transfer Asset Data from ServiceExchange to Bigfix']/.//targetadapter[@displayname='Bigfix Adapter']").findall(".//device_properties/*") if p.attrib.get("propertyname") == "ID"), None)
                        computer_id = record.get(bigfix_ID_propName)
                        mailbox_manager.process_and_delete_cmdb_files(computer_id)
                        response = mailbox_manager.post_file(payload, computer_id)
                        if response and response.status_code == 200:
                            logger.info(f"Data for computer ID {computer_id} pushed successfully.")
                        else:
                            logger.error(f"Failed to push data for computer ID {computer_id}. Response: {response}")
            else:
                logger.info("No correlation found between BigFix and ServiceExchange Computer Data.")
    except Exception as e:
        logger.error(f"Error during processing: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BigFix Adapter Main Script")
    
    # Flags for various functionalities
    parser.add_argument("--providecredentials", action="store_true", help="Provide credentials manually")
    parser.add_argument("--init", action="store_true", help="Initialize the connection validation")
    parser.add_argument("--provideproxycredentials", action="store_true", help="Provide proxy credentials manually")
    parser.add_argument("--reset", action="store_true", help="Reset the CMDB hash in the XML config")

    # Parse command-line arguments
    args = parser.parse_args()

    # Call the main function with parsed arguments
    main(
        provide_credentials=args.providecredentials,
        init=args.init,
        provide_proxy_credentials=args.provideproxycredentials,
        reset=args.reset
    )