import redis
import json
from flask import current_app

class RedisClient:
    def __init__(self):
        self.redis_client = None
    
    def init_app(self, app):
        self.redis_client = redis.Redis(
            host=app.config['REDIS_HOST'],
            port=app.config['REDIS_PORT'],
            db=app.config['REDIS_DB'],
            decode_responses=True
        )
    
    def get_connection(self):
        return self.redis_client
    
    def publish_message(self, channel, message):
        """Publica mensagem no canal Pub/Sub"""
        self.redis_client.publish(channel, json.dumps(message))
    
    def subscribe_to_channel(self, channel):
        """Cria uma subscription para um canal"""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(channel)
        return pubsub
    
    def set_auction_data(self, auction_id, data, expire_hours=24):
        """Armazena dados do leilão com expiração"""
        key = f"auction:{auction_id}"
        print(f"Setting auction data for {key}: {data}")
        
        # Converter valores booleanos para string
        redis_data = {}
        for k, v in data.items():
            if isinstance(v, bool):
                redis_data[k] = 'true' if v else 'false'
            else:
                redis_data[k] = str(v) if v is not None else ''
        
        self.redis_client.hset(key, mapping=redis_data)
        self.redis_client.expire(key, expire_hours * 3600)
        
        # Adiciona ao conjunto de leilões ativos
        self.redis_client.sadd("active_auctions", auction_id)
        print(f"Auction {auction_id} added to active_auctions set")
    
    def get_auction_data(self, auction_id):
        """Recupera dados do leilão"""
        key = f"auction:{auction_id}"
        data = self.redis_client.hgetall(key)
        
        if not data:
            return None
        
        # Garantir que todos os campos existam
        default_fields = {
            'current_winner': '',
            'current_winner_id': ''
        }
        
        for field, default_value in default_fields.items():
            if field not in data:
                data[field] = default_value
        
        # Converter tipos (se você ainda não tiver essa parte)
        try:
            if 'current_price' in data:
                data['current_price'] = float(data['current_price'])
        except (ValueError, TypeError):
            data['current_price'] = 0.0
            
        try:
            if 'starting_price' in data:
                data['starting_price'] = float(data['starting_price'])
        except (ValueError, TypeError):
            data['starting_price'] = 0.0
            
        try:
            if 'bid_count' in data:
                data['bid_count'] = int(data['bid_count'])
        except (ValueError, TypeError):
            data['bid_count'] = 0
        
        return data
    
    def add_bid_to_auction(self, auction_id, bid_data):
        """Adiciona lance ao histórico do leilão"""
        bid_list_key = f"auction:{auction_id}:bids"
        
        # Adiciona lance à lista ordenada por timestamp
        timestamp = float(bid_data.get('timestamp', 0))
        self.redis_client.zadd(
            bid_list_key,
            {json.dumps(bid_data): timestamp}
        )
        
        # Mantém apenas os últimos 100 lances
        self.redis_client.zremrangebyrank(bid_list_key, 0, -101)
        
        # Atualiza o maior lance
        try:
            amount = float(bid_data.get('amount', 0))
            self.update_highest_bid(auction_id, amount)
        except (ValueError, TypeError) as e:
            print(f"Error updating highest bid: {e}")
    
    def update_highest_bid(self, auction_id, amount, user_id=None, username=None):
        """Atualiza o maior lance do leilão e o vencedor atual"""
        key = f"auction:{auction_id}"
        try:
            self.redis_client.hset(key, 'current_price', str(amount))
            self.redis_client.hincrby(key, 'bid_count', 1)
            
            # Atualiza o vencedor atual se fornecido
            if username:
                self.redis_client.hset(key, 'current_winner', str(username))
            if user_id:
                self.redis_client.hset(key, 'current_winner_id', str(user_id))
                
        except Exception as e:
            print(f"Error updating highest bid in Redis: {e}")
        
    def get_auction_bids(self, auction_id, limit=10):
        """Recupera últimos lances do leilão"""
        bid_list_key = f"auction:{auction_id}:bids"
        bids = self.redis_client.zrevrange(bid_list_key, 0, limit-1)
        
        result = []
        for bid_json in bids:
            try:
                bid_data = json.loads(bid_json)
                # Converter valores numéricos de volta
                if 'amount' in bid_data:
                    try:
                        bid_data['amount'] = float(bid_data['amount'])
                    except (ValueError, TypeError):
                        pass
                if 'timestamp' in bid_data:
                    try:
                        bid_data['timestamp'] = float(bid_data['timestamp'])
                    except (ValueError, TypeError):
                        pass
                result.append(bid_data)
            except json.JSONDecodeError as e:
                print(f"Error parsing bid JSON: {e}")
        
        return result
    
    def get_active_auctions(self):
        """Retorna lista de IDs de leilões ativos"""
        return self.redis_client.smembers("active_auctions")
    
    def close_auction(self, auction_id):
        """Encerra um leilão"""
        self.redis_client.srem("active_auctions", auction_id)
        key = f"auction:{auction_id}"
        self.redis_client.hset(key, 'active', 'false')

redis_client = RedisClient()