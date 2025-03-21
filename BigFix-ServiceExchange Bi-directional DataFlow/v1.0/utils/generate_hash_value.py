import hashlib
import xml.etree.ElementTree as ET
import time

class CryptoServices:
    __instance = None

    def __new__(cls):
        if CryptoServices.__instance is None:
            CryptoServices.__instance = object.__new__(cls)
        return CryptoServices.__instance

    @staticmethod
    def generate_unique_hash(config_path):
        tree = ET.parse(config_path)
        root = tree.getroot()
        
        # Generate a new hash based on the timestamp
        unique_hash = hashlib.sha1(str(int(time.time())).encode('utf-8')).hexdigest()
        
        # Update the unique_hash attribute
        root.set("uniquehash", unique_hash)
        
        # Save changes back to the XML file
        tree.write(config_path, encoding="utf-8", xml_declaration=True)
        
        print(f"New Unique Hash Generated: {unique_hash}")
        return unique_hash