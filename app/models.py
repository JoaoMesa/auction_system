from datetime import datetime, timezone
import uuid

class Auction:
    def __init__(self, title, description, starting_price, end_time, owner_id):
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.starting_price = float(starting_price)
        self.current_price = float(starting_price)
        self.end_time = end_time
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.owner_id = owner_id
        self.active = True
        self.bid_count = 0
        
    def to_dict(self):
        """Converter para dicionário com tipos compatíveis com Redis"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'starting_price': str(self.starting_price),  # String para Redis
            'current_price': str(self.current_price),    # String para Redis
            'end_time': self.end_time,
            'created_at': self.created_at,
            'owner_id': self.owner_id,
            'active': 'true' if self.active else 'false',  # String para Redis
            'bid_count': str(self.bid_count),  # String para Redis
            #'current_winner': str(self.current_winner) if self.current_winner else '',  # NOVO
            #'current_winner_id': str(self.current_winner_id) if self.current_winner_id else ''  # NOVO
        }
    
    def is_active(self):
        """Verifica se o leilão ainda está ativo"""
        try:
            if 'Z' in self.end_time:
                end_time = datetime.fromisoformat(self.end_time.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            else:
                end_time = datetime.fromisoformat(self.end_time)
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)
            
            current_time = datetime.now(timezone.utc)
            return current_time < end_time and self.active
        except:
            return False

class Bid:
    def __init__(self, auction_id, user_id, amount, username=None):
        self.id = str(uuid.uuid4())
        self.auction_id = auction_id
        self.user_id = user_id
        self.username = username or f"User_{user_id}"
        self.amount = float(amount)
        self.timestamp = datetime.now(timezone.utc).timestamp()
        
    def to_dict(self):
        return {
            'id': self.id,
            'auction_id': self.auction_id,
            'user_id': self.user_id,
            'username': self.username,
            'amount': str(self.amount),  # String para Redis
            'timestamp': str(self.timestamp)  # String para Redis
        }