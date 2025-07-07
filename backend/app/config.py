from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings with automatic loading from .env file"""
    
    # Database configuration
    mongo_uri: str = Field(alias="MONGODB_URI")
    mongo_db_name: str = Field(default="fusevault", alias="MONGO_DB_NAME")
    
    # Blockchain settings
    wallet_address: str = Field(alias="WALLET_ADDRESS")
    private_key: str = Field(alias="PRIVATE_KEY")
    alchemy_sepolia_url: str = Field(alias="ALCHEMY_SEPOLIA_URL")
    contract_address: Optional[str] = Field(None, alias="CONTRACT_ADDRESS")
    
    # Web3 Storage settings
    web3_storage_service_url: str = Field(default="http://localhost:8080", alias="WEB3_STORAGE_SERVICE_URL")
    
    # JWT settings
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=1440, alias="JWT_EXPIRATION_MINUTES")  # 24 hours
    
    # Application settings
    debug: bool = Field(default=False, alias="DEBUG")
    cors_origins: str = Field(default="http://localhost:3001", alias="CORS_ORIGINS")
    is_production: bool = Field(default=False, alias="IS_PRODUCTION")
    
    # API Key settings (new)
    api_key_auth_enabled: bool = Field(default=False, alias="API_KEY_AUTH_ENABLED")
    api_key_secret_key: Optional[str] = Field(None, alias="API_KEY_SECRET_KEY")
    api_key_rate_limit_per_minute: int = Field(default=100, alias="API_KEY_RATE_LIMIT_PER_MINUTE")
    api_key_max_per_wallet: int = Field(default=10, alias="API_KEY_MAX_PER_WALLET")
    api_key_default_expiration_days: int = Field(default=90, alias="API_KEY_DEFAULT_EXPIRATION_DAYS")
    api_key_default_permissions: List[str] = Field(default=["read"], alias="API_KEY_DEFAULT_PERMISSIONS")
    
    # Redis settings (for rate limiting)
    redis_url: Optional[str] = Field(None, alias="REDIS_URL")
    
    @validator("api_key_secret_key")
    def validate_api_key_secret(cls, v, values):
        """Ensure API key secret is set and secure when API keys are enabled"""
        if values.get("api_key_auth_enabled") and not v:
            raise ValueError("API_KEY_SECRET_KEY is required when API_KEY_AUTH_ENABLED is true")
        if v and len(v) < 32:
            raise ValueError("API_KEY_SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("redis_url")
    def validate_redis_for_api_keys(cls, v, values):
        """Ensure Redis URL is set when API keys are enabled (required for rate limiting)"""
        if values.get("api_key_auth_enabled") and not v:
            raise ValueError(
                "REDIS_URL is required when API_KEY_AUTH_ENABLED is true. "
                "API key rate limiting requires Redis for security."
            )
        return v
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        if isinstance(self.cors_origins, str):
            if "," in self.cors_origins:
                return [origin.strip() for origin in self.cors_origins.split(",")]
            return [self.cors_origins.strip()]
        return self.cors_origins
    
    class Config:
        # Load from backend-specific .env file (for local development)
        # Railway deployment uses environment variables directly
        env_file = [".env"]
        env_file_encoding = 'utf-8'
        case_sensitive = False
        
        
# Create a singleton instance
settings = Settings()