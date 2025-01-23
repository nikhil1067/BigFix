import keyring
from utils.logger import logger

class CredentialManager:
    def __init__(self, service_name):
        """Initialize with a service name to namespace credentials."""
        self.service_name = service_name

    def add_credential(self, username, password):
        """Store credentials securely using the keyring library."""
        try:
            keyring.set_password(self.service_name, username, password)
            logger.info(f"Credential for {self.service_name} stored successfully.")
        except Exception as e:
            logger.error(f"Error adding credential: {e}")

    def retrieve_password(self, username):
        """Retrieve stored credentials using the keyring library."""
        try:
            password = keyring.get_password(self.service_name, username)
            if password is None:
                logger.warning(f"No credentials found for {self.service_name} with username '{username}'.")
                return None
            return password
        except Exception as e:
            logger.error(f"Error retrieving credential: {e}")
            return None

    def delete_credential(self, username):
        """Delete a stored credential using the keyring library."""
        try:
            keyring.delete_password(self.service_name, username)
            logger.info(f"Credential for {self.service_name} with username '{username}' deleted successfully.")
        except Exception as e:
            logger.error(f"Error deleting credential: {e}")