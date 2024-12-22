import os 
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
    firebase_project_id: str
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
    def fcm_access_token(self) -> str:
        """Retrieve and cache the access token, if not already cached."""
        if self._fcm_access_token is None:
            self._fcm_access_token = _get_access_token(service_account_json_path=self.service_account_json_path)
        return self._fcm_access_token
    
    @property
    def service_account_json_path(self) -> str:
        if self._service_account_json_path is None :
            self._service_account_json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),self.service_account_json_name)
        return self._service_account_json_path

    class Config:
        env_file = env_path

settings = Settings()


def _get_access_token(service_account_json_path: str) :
    try :
        credentials = service_account.Credentials.from_service_account_file(
        service_account_json_path, scopes=["https://www.googleapis.com/auth/firebase.messaging"])
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        if not credentials.token:
            raise ValueError("Failed to retrieve access token.")
        return credentials.token
    except Exception as e:
        # Log the full error and response for debugging
        custom_logger.exception(f"Error: {str(e)}",stack_info=True) 
    
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