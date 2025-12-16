import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    REDIS_HOST = os.environ.get("REDIS_HOST", "redis")

    # NUNCA use REDIS_PORT direto (k8s sobrescreve)
    REDIS_PORT = int(os.environ.get("REDIS_SERVICE_PORT", 6379))

    REDIS_DB = int(os.environ.get("REDIS_DB", 0))
    
    # Configurações do leilão
    BID_INCREMENT_PERCENT = 5
    AUCTION_EXPIRE_HOURS = 24
    
    # Configurações para múltiplas instâncias
    SESSION_COOKIE_NAME = 'auction_session'
    JSON_SORT_KEYS = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # Para produção, desativar detalhes de erro
    PROPAGATE_EXCEPTIONS = True