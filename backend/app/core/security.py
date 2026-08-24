import os
import logging
from typing import Optional
from pathlib import Path
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

SERVICE_NAME = "TarjumanApp"
KEY_USERNAME = "GeminiApiKey"

class CredentialManager:
    """
    Secure credential manager for Tarjuman.
    Prioritizes:
    1. Environment Variable GEMINI_API_KEY
    2. macOS Keychain (via keyring)
    3. Secure restricted permission file (~/.tarjuman/.secret_key)
    """

    @classmethod
    def get_gemini_api_key(cls) -> Optional[str]:
        # 1. Environment Variable
        env_key = os.getenv("GEMINI_API_KEY")
        if env_key and env_key.strip():
            return env_key.strip()
        
        # 2. macOS Keychain
        try:
            import keyring
            keychain_val = keyring.get_password(SERVICE_NAME, KEY_USERNAME)
            if keychain_val and keychain_val.strip():
                return keychain_val.strip()
        except Exception as e:
            logger.debug(f"Keychain read unavailable: {e}")
            
        # 3. File fallback with restricted permissions
        secret_file = settings.DATA_DIR / ".secret_gemini"
        if secret_file.exists():
            try:
                content = secret_file.read_text(encoding="utf-8").strip()
                if content:
                    return content
            except Exception as e:
                logger.error(f"Failed to read secret file: {e}")
                
        return None

    @classmethod
    def set_gemini_api_key(cls, api_key: str) -> bool:
        api_key = api_key.strip()
        saved = False
        
        # Try saving to macOS Keychain
        try:
            import keyring
            keyring.set_password(SERVICE_NAME, KEY_USERNAME, api_key)
            saved = True
        except Exception as e:
            logger.warning(f"Could not save to Keychain: {e}")
            
        # Save to local restricted file as safe backup/fallback
        try:
            secret_file = settings.DATA_DIR / ".secret_gemini"
            secret_file.write_text(api_key, encoding="utf-8")
            # Set mode to 0600 (owner read/write only)
            os.chmod(secret_file, 0o600)
            saved = True
        except Exception as e:
            logger.error(f"Failed to save secret file: {e}")
            
        return saved

    @classmethod
    def delete_gemini_api_key(cls) -> bool:
        deleted = False
        try:
            import keyring
            keyring.delete_password(SERVICE_NAME, KEY_USERNAME)
            deleted = True
        except Exception:
            pass
            
        secret_file = settings.DATA_DIR / ".secret_gemini"
        if secret_file.exists():
            try:
                secret_file.unlink()
                deleted = True
            except Exception as e:
                logger.error(f"Failed to delete secret file: {e}")
        return deleted
