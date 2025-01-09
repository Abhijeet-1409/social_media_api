import os 
import time
import asyncio
from app.logger import custom_logger
from google.oauth2 import service_account
from pydantic_settings import BaseSettings
import google.auth.transport.requests

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),".env")

class Settings(BaseSettings) :
    # fcm_url: str
    algorithm: str
    secret_key: str
    mongo_user: str
    mongo_db_name: str
    mongo_options: str
    mongo_cluster: str
    mongo_password: str
    firebase_api_key: str
    firebase_auth_domain: str
    firebase_project_id: str
    firebase_storage_bucket: str
    firebase_messaging_sender_id: str
    firebase_app_id: str
    firebase_measurement_id: str
    vapid_key:str
    service_account_json_name: str
    access_token_expire_minutes: int

    _fcm_access_token: str = None
    _service_account_json_path: str = None


    @property
    def mongo_uri(self) -> str:
        return f"mongodb+srv://{self.mongo_user}:{self.mongo_password}@{self.mongo_cluster}/{self.mongo_db_name}?{self.mongo_options}"

    @property
    def fcm_url(self) -> str:
        return f"https://fcm.googleapis.com/v1/projects/{self.firebase_project_id}/messages:send"
    
    @property
    def firebase_clientside_config(self) -> dict[str,str]:
        firebase_config: dict[str,str] =  {
            "apiKey": self.firebase_api_key,
            "authDomain": self.firebase_auth_domain,
            "projectId": self.firebase_project_id,
            "storageBucket": self.firebase_storage_bucket,
            "messagingSenderId": self.firebase_messaging_sender_id,
            "appId": self.firebase_app_id,
            "measurementId": self.firebase_measurement_id
        }
        return firebase_config

    @property
    async def fcm_access_token(self) -> str:
        """Retrieve and cache the access token asynchronously."""
        if self._fcm_access_token is None or self._is_token_expired():
            self._fcm_access_token = await _get_access_token(service_account_json_path=self.service_account_json_path)
            self._token_timestamp = time.time()  # Update timestamp when new token is retrieved
        return self._fcm_access_token

    def _is_token_expired(self) -> bool:
        """Check if the access token has expired."""
        expiration_time = 3600  # Set expiration time (e.g., 1 hour)
        return (self._token_timestamp is None) or (time.time() - self._token_timestamp > expiration_time)

    @property
    def service_account_json_path(self) -> str:
        if self._service_account_json_path is None :
            self._service_account_json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),self.service_account_json_name)
        return self._service_account_json_path

    class Config:
        env_file = env_path

settings = Settings()


async def _get_access_token(service_account_json_path: str) -> str:
    try:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_json_path,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"]
        )
        request = google.auth.transport.requests.Request()
        await asyncio.to_thread(credentials.refresh, request)  # Run refresh in a separate thread
        if not credentials.token:
            raise ValueError("Failed to retrieve access token.")
        return credentials.token
    except Exception as e:
        custom_logger.exception(f"Error retrieving access token: {str(e)}", stack_info=True)
    
    return None




if __name__ == "__main__" :
    settings_json = settings.model_dump()
    settings_json.update({
        "fcm_access_token" : settings.fcm_access_token,
        "mongo_uri": settings.mongo_uri,
        "fcm_url": settings.fcm_url,
        "service_account_json_path": settings.service_account_json_path,
    })
    
    for key , value in settings_json.items() : 
        print(f"{key} : {value}")