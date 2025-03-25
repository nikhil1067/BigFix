import ctypes
from ctypes import wintypes
import logging

logger = logging.getLogger("service_logger")

CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2

LPBYTE = ctypes.POINTER(ctypes.c_ubyte)

class CREDENTIAL_ATTRIBUTE(ctypes.Structure):
    _fields_ = [
        ('Keyword', wintypes.LPWSTR),
        ('Flags', wintypes.DWORD),
        ('ValueSize', wintypes.DWORD),
        ('Value', LPBYTE),
    ]

class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ('Flags', wintypes.DWORD),
        ('Type', wintypes.DWORD),
        ('TargetName', wintypes.LPWSTR),
        ('Comment', wintypes.LPWSTR),
        ('LastWritten', wintypes.FILETIME),
        ('CredentialBlobSize', wintypes.DWORD),
        ('CredentialBlob', LPBYTE),
        ('Persist', wintypes.DWORD),
        ('AttributeCount', wintypes.DWORD),
        ('Attributes', ctypes.POINTER(CREDENTIAL_ATTRIBUTE)),
        ('TargetAlias', wintypes.LPWSTR),
        ('UserName', wintypes.LPWSTR),
    ]

advapi32 = ctypes.WinDLL('Advapi32.dll')
CredWriteW = advapi32.CredWriteW
CredWriteW.argtypes = [ctypes.POINTER(CREDENTIAL), wintypes.DWORD]
CredWriteW.restype = wintypes.BOOL

class CredentialManager:
    def __init__(self, service_name):
        self.service_name = service_name

    def _build_target(self, username):
        return f"{username}@{self.service_name}"

    def add_credential(self, username, password):
        try:
            target = self._build_target(username)
            blob = password.encode("utf-16le")
            blob_size = len(blob)

            blob_buffer = (ctypes.c_ubyte * blob_size).from_buffer_copy(blob)

            cred = CREDENTIAL()
            cred.Flags = 0
            cred.Type = CRED_TYPE_GENERIC
            cred.TargetName = target
            cred.Comment = None
            cred.LastWritten = wintypes.FILETIME(0, 0)
            cred.CredentialBlobSize = blob_size
            cred.CredentialBlob = ctypes.cast(blob_buffer, LPBYTE)
            cred.Persist = CRED_PERSIST_LOCAL_MACHINE
            cred.AttributeCount = 0
            cred.Attributes = None
            cred.TargetAlias = None
            cred.UserName = username

            if not CredWriteW(ctypes.byref(cred), 0):
                raise ctypes.WinError()

            logger.info(f"Credential stored successfully for {target} (raw WinAPI)")

        except Exception as e:
            logger.error(f"Error adding credential for {username}: {e}")

    def retrieve_password(self, username):
        try:
            import ctypes
            from ctypes import wintypes

            target = self._build_target(username)

            # Define structures
            class CREDENTIAL(ctypes.Structure):
                _fields_ = [
                    ('Flags', wintypes.DWORD),
                    ('Type', wintypes.DWORD),
                    ('TargetName', wintypes.LPWSTR),
                    ('Comment', wintypes.LPWSTR),
                    ('LastWritten', wintypes.FILETIME),
                    ('CredentialBlobSize', wintypes.DWORD),
                    ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)),
                    ('Persist', wintypes.DWORD),
                    ('AttributeCount', wintypes.DWORD),
                    ('Attributes', ctypes.c_void_p),
                    ('TargetAlias', wintypes.LPWSTR),
                    ('UserName', wintypes.LPWSTR),
                ]

            PCREDENTIAL = ctypes.POINTER(CREDENTIAL)

            CredReadW = ctypes.windll.advapi32.CredReadW
            CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(PCREDENTIAL)]
            CredReadW.restype = wintypes.BOOL

            CredFree = ctypes.windll.advapi32.CredFree

            cred_ptr = PCREDENTIAL()
            if CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(cred_ptr)):
                cred = cred_ptr.contents
                size = cred.CredentialBlobSize
                blob = ctypes.string_at(cred.CredentialBlob, size)
                CredFree(cred_ptr)
                password = blob.decode("utf-16le")
                logger.info(f"Retrieved credential for {target} via WinAPI")
                return password
            else:
                logger.warning(f"No credentials found via WinAPI for {self.service_name} with username '{username}'.")
                return None

        except Exception as e:
            logger.error(f"Error retrieving credential for {username}: {e}")
            return None