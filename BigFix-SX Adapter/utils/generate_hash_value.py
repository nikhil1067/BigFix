import hashlib
import platform
import uuid

class CryptoServices:
    __instance = None

    def __new__(cls):
        if CryptoServices.__instance is None:
            CryptoServices.__instance = object.__new__(cls)
        return CryptoServices.__instance

    @staticmethod
    def generate_unique_hash():
        """
        Generate a unique hash based on the machine's hostname and UUID.

        Returns:
            str: A unique hash value using SHA-1.
        """
        # Get the machine hostname
        hostname = platform.node()
        
        # Get the machine UUID
        machine_uuid = str(uuid.UUID(int=uuid.getnode()))
        
        # Combine the hostname and UUID to create a unique input
        unique_data = f"{hostname}|{machine_uuid}"
        
        # Create a SHA-1 hash from the combined data
        hash_object = hashlib.sha1(unique_data.encode('utf-8'))
        unique_hash = hash_object.hexdigest()
        
        return unique_hash