def main(provide_credentials=False):
    from utils.logger import logger
    from utils.config_loader import load_config
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
    import getpass
    import csv
    from sys import exit

    config_path = r"C:\BigFix-SX Adapter\config.xml"
    preview_records_path = r"C:\BigFix-SX Adapter\Preview_Records.csv"
    cache_path = r"C:\BigFix-SX Adapter\RecordsCache.dat"

    # Generate a unique hash
    crypto_services = CryptoServices()
    unique_hash = crypto_services.generate_unique_hash()
    # Load configuration
    config = load_config(config_path)
    SETTINGS = config['dataflowconfig']['settings']['setting']
    if isinstance(SETTINGS, dict):
        settings = [SETTINGS]
    else:
        settings = SETTINGS

    # Check PREVIEW_ONLY setting
    preview_only = next((item['value'].upper() == 'TRUE' for item in settings if item['key'] == 'PREVIEW_ONLY'), False)

    # Initialize credentials management
    service = next(item['value'] for item in settings if item['key'] == 'LOCKER_SERVICE_NAME')
    credentials_manager = CredentialManager(service)
    config_writer = ConfigWriter(config_path)

    BIGFIX_CONFIG = config['dataflowconfig']['bigfix']
    SX_CONFIG = config['dataflowconfig']['sx']

    # Handle credentials
    if provide_credentials:
        bigfix_username = input("Enter BigFix Master Operator username: ")
        bigfix_password = getpass.getpass("Enter BigFix Master Operator password: ")
        credentials_manager.add_credential(bigfix_username, bigfix_password)
        config_writer.write_username("bigfix", bigfix_username)

        sx_username = input("Enter Service Exchange API username: ")
        sx_password = getpass.getpass("Enter Service Exchange API password: ")
        credentials_manager.add_credential(sx_username, sx_password)
        config_writer.write_username("sx", sx_username)
        return

    # Retrieve credentials
    bigfix_username = BIGFIX_CONFIG['credentials']['username']['value']
    bigfix_password = credentials_manager.retrieve_password(bigfix_username)

    sx_username = SX_CONFIG['credentials']['username']['value']
    sx_password = credentials_manager.retrieve_password(sx_username)

    # Extract dynamic properties
    bigfix_properties = {prop["name"]: prop["name"] for prop in BIGFIX_CONFIG['properties']['property']}
    sx_properties = {prop["name"]: prop["name"] for prop in SX_CONFIG['properties']['property']}
    record_limit = next((item['value'] for item in settings if item['key'] == 'RECORD_LIMIT_PER_PAGE'), None)
    data_flow_direction = next((item['value'] for item in settings if item['key'] == 'DATA_FLOW_DIRECTION'), 'BOTH')

    bigfix_api = BigFixAPIHandler(config_path, BIGFIX_CONFIG['api_url']['value'], bigfix_username, bigfix_password)
    sx_api = SXAPIHandler(config_path, record_limit, SX_CONFIG['api_url']['value'], sx_username, sx_password)

    mailbox_manager = MailboxManager(BIGFIX_CONFIG['api_url']['value'], bigfix_username, bigfix_password, unique_hash)
    analysis_manager = BigFixAnalysisHandler(BIGFIX_CONFIG['api_url']['value'], bigfix_username, bigfix_password, BIGFIX_CONFIG['site_name']['value'], unique_hash)
    properties = PropertiesExtractor(config_path)
    bes_site = BigFixSiteHandler(BIGFIX_CONFIG['api_url']['value'], bigfix_username, bigfix_password, BIGFIX_CONFIG['site_name']['value'])
    cache = CacheManager(cache_path)

    try:
        if not bes_site.get_site():
            logger.error("BigFix site does not exist.")
            exit(100)

        logger.info("Fetching data from BigFix...")
        bigfix_data = bigfix_api.get_computer_data() or []
        logger.info("Fetching data from SX...")
        sx_data = sx_api.get_computer_data() or []

        if not bigfix_data or not sx_data:
            logger.error("Data not available to correlate.")
            exit(100)

        cached_bigfix_data = cache.load_from_cache('bigfix_data') or []
        cached_sx_data = cache.load_from_cache('sx_data') or []

        new_bigfix_data = [data for data in bigfix_data if data not in cached_bigfix_data]
        new_sx_data = [data for data in sx_data if data not in cached_sx_data]

        if not new_bigfix_data and not new_sx_data:
            logger.info("No new or changed data to process.")
            exit(0)

        cache.save_to_cache('bigfix_data', bigfix_data)
        cache.save_to_cache('sx_data', sx_data)
        correlated_data = None

        if data_flow_direction in ['BIGFIX_TO_SX', 'BOTH'] and new_bigfix_data:
            logger.info("Sending new BigFix data to Service Exchange...")
            for data in new_bigfix_data:
                sx_api.post_computer_details(data)

        if data_flow_direction in ['SX_TO_BIGFIX', 'BOTH'] and new_sx_data:
            logger.info("Processing new Service Exchange data...")
            correlated_data = DataCorrelation.correlate(new_bigfix_data, sx_data, bigfix_properties, sx_properties)
        property_headers = list(bigfix_properties.keys()) + list(sx_properties.keys())
        if correlated_data:
            if preview_only:
                # Create CSV file of the data
                with open(preview_records_path, mode='w', newline='') as file:
                    csv_writer = csv.writer(file)
                    csv_writer.writerow(property_headers)
                    # Write rows
                    for record in correlated_data:
                        csv_writer.writerow(record.values())
                logger.info("Preview mode enabled. Data saved to 'preview_data.csv'.")
                return
            else:
                logger.info("Creating BigFix analysis...")
                analysis_name = "ServiceExchange Custom Properties"
                analysis_description = "Analysis of correlated data between BigFix and SX systems."
                property_names = properties.extract_properties()
                extracted_properties = analysis_manager.get_properties(property_names)
                payload = analysis_manager.generate_analysis_payload(analysis_name, analysis_description, extracted_properties)

                analysis_id = analysis_manager.get_analysis_id()
                if analysis_id:
                    analysis_manager.put_analysis(analysis_id, payload)
                else:
                    analysis_manager.post_analysis(payload)

                for record in correlated_data:
                    payload = ",".join(str(record.get(prop, "")).replace(",", ";") for prop in properties.extract_properties())
                    computer_id = record.get(bigfix_properties.get("ID"))
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
    parser.add_argument("--providecredentials", action="store_true", help="Provide credentials manually")
    args = parser.parse_args()

    main(provide_credentials=args.providecredentials)