import os 
from pydantic_settings import BaseSettings


env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),".env")

class Settings(BaseSettings) :
    fcm_url: str
    algorithm: str
    secret_key: str
    mongo_user: str
    mongo_db_name: str
    mongo_options: str
    mongo_cluster: str
    fcm_server_key: str
    mongo_password: str
    access_token_expire_minutes: int
    
    @property
    def mongo_uri(self) -> str:
        return f"mongodb+srv://{self.mongo_user}:{self.mongo_password}@{self.mongo_cluster}/{self.mongo_db_name}?{self.mongo_options}"

    class Config:
        env_file = env_path

settings = Settings()