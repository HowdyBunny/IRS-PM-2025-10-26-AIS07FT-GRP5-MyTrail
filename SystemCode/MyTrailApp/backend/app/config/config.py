from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Google Maps API configuration
    google_maps_api_key: str = "****REDACTED****"

    # API configuration
    api_version: str = "1.0"
    max_routes: int = 3

    # API call limits
    max_api_calls_per_day: int = 1000

    # OpenAI configuration
    openai_model: str = "gpt-4o-mini"
    
    # openai_api_key: str = "sk-xxx" 
    # openai_base_url: str | None = None
    # TODO: Now for economic use, I set POE model first, set url to POE API endpoint:https://api.poe.com/v1
    openai_api_key: str  = "****REDACTED****"
    openai_base_url: str = "https://api.poe.com/v1"

    # Basic NLU model configuration
    nlu_basic_model_url: str = "http://192.168.0.207:4000/predict"

    # MongoDB configuration for feedback storage
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "mytrail"
    mongo_feedback_collection: str = "route_feedback"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
