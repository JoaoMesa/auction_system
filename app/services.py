from datetime import datetime, timedelta, timezone
from app.models import Auction, Bid
from app.redis_client import redis_client

class AuctionService:
    @staticmethod
    def create_auction(title, description, starting_price, end_time, owner_id):
        """Cria um novo leilão"""
        print(f"Creating auction: {title}, price: {starting_price}, owner: {owner_id}, end_time: {end_time}")
        
        # Validação do tempo de término
        try:
            # Converter para datetime com timezone UTC
            if 'Z' in end_time:
                end_datetime = datetime.fromisoformat(end_time.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            else:
                end_datetime = datetime.fromisoformat(end_time)
                # Se não tem timezone, assumir UTC
                if end_datetime.tzinfo is None:
                    end_datetime = end_datetime.replace(tzinfo=timezone.utc)
            
            # Usar datetime UTC atual
            current_time = datetime.now(timezone.utc)
            print(f"Current time (UTC): {current_time}")
            print(f"End time: {end_datetime}")
            
            if end_datetime <= current_time:
                print("End time is in the past")
                return None, "End time must be in the future"
                
        except ValueError as e:
            print(f"Invalid date format: {end_time}, error: {e}")
            return None, f"Invalid date format: {end_time}. Use ISO format (e.g., 2024-12-31T23:59:59Z)"
        
        # Validação do preço
        try:
            starting_price = float(starting_price)
            if starting_price <= 0:
                return None, "Starting price must be greater than 0"
        except ValueError:
            return None, "Invalid starting price"
        
        # Cria o leilão
        auction = Auction(
            title=title,
            description=description,
            starting_price=starting_price,
            end_time=end_time,
            owner_id=owner_id
        )
        
        print(f"Auction object created: {auction.id}")
        
        try:
            # Salva no Redis - USANDO O MÉTODO CORRETO
            # O redis_client.set_auction_data já deve converter boolean para string
            redis_client.set_auction_data(auction.id, auction.to_dict())

            redis_client.get_connection().hset(f"auction:{auction.id}", 'current_winner', '')
            redis_client.get_connection().hset(f"auction:{auction.id}", 'current_winner_id', '')

            print(f"Auction saved to Redis: {auction.id}")
        except Exception as e:
            print(f"Error saving to Redis: {e}")
            import traceback
            traceback.print_exc()
            return None, f"Database error: {e}"
        
        return auction, None
    
    @staticmethod
    def get_auction(auction_id):
        """Recupera um leilão pelo ID"""
        data = redis_client.get_auction_data(auction_id)
        if not data:
            return None
        
        # CONVERTER TODOS OS CAMPOS IMPORTANTES
        # Garantir que os campos de vencedor existam
        if 'current_winner' not in data:
            data['current_winner'] = ''
        
        if 'current_winner_id' not in data:
            data['current_winner_id'] = ''
        
        # Converter tipos numéricos
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
        
        print(f"DEBUG - get_auction for {auction_id}:")
        print(f"  current_winner: {data.get('current_winner')}")
        print(f"  current_winner_id: {data.get('current_winner_id')}")
        
        return data

    @staticmethod
    def get_active_auctions():
        """Retorna todos os leilões ativos"""
        print("=== Getting active auctions ===")
        try:
            active_auction_ids = redis_client.get_active_auctions()
            print(f"Active auction IDs: {active_auction_ids}")
            
            auctions = []
            
            for auction_id in active_auction_ids:
                try:
                    auction_data = redis_client.get_auction_data(auction_id)
                    if auction_data:
                        # Verificar se está ativo
                        is_active = auction_data.get('active', 'false') == 'true'
                        
                        if is_active:
                            # GARANTIR QUE OS CAMPOS DE VENCEDOR EXISTAM
                            if 'current_winner' not in auction_data:
                                auction_data['current_winner'] = ''
                            
                            if 'current_winner_id' not in auction_data:
                                auction_data['current_winner_id'] = ''
                            
                            # Converter tipos
                            try:
                                auction_data['current_price'] = float(auction_data.get('current_price', 0))
                            except:
                                auction_data['current_price'] = 0.0
                                
                            try:
                                auction_data['starting_price'] = float(auction_data.get('starting_price', 0))
                            except:
                                auction_data['starting_price'] = 0.0
                                
                            try:
                                auction_data['bid_count'] = int(auction_data.get('bid_count', 0))
                            except:
                                auction_data['bid_count'] = 0
                            
                            print(f"DEBUG - Auction {auction_id} winner: {auction_data.get('current_winner')}")
                            
                            auctions.append(auction_data)
                except Exception as e:
                    print(f"Error processing auction {auction_id}: {e}")
                    continue
            
            print(f"Found {len(auctions)} active auctions")
            return auctions
            
        except Exception as e:
            print(f"Error in get_active_auctions: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def close_expired_auctions():
        """Fecha leilões expirados - VERSÃO SIMPLIFICADA"""
        print("=== Checking expired auctions ===")
        try:
            active_auction_ids = redis_client.get_active_auctions()
            current_time = datetime.now(timezone.utc)
            
            for auction_id in active_auction_ids:
                try:
                    auction_data = redis_client.get_auction_data(auction_id)
                    if auction_data and auction_data.get('active', 'false') == 'true':
                        # Verificar tempo de término
                        end_time_str = auction_data.get('end_time', '')
                        if end_time_str:
                            try:
                                # Converter string para datetime
                                if 'Z' in end_time_str:
                                    end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
                                else:
                                    end_time = datetime.fromisoformat(end_time_str)
                                    if end_time.tzinfo is None:
                                        end_time = end_time.replace(tzinfo=timezone.utc)
                                
                                if current_time >= end_time:
                                    print(f"Closing expired auction: {auction_id}")
                                    redis_client.close_auction(auction_id)

                                    redis_client.publish_message("leiloes_finalizados",
                                    {"auction_id": auction_id}
                                    )

                            except Exception as e:
                                print(f"Error checking time for auction {auction_id}: {e}")
                except Exception as e:
                    print(f"Error processing auction {auction_id}: {e}")
                    continue
        except Exception as e:
            print(f"Error in close_expired_auctions: {e}")
            import traceback
            traceback.print_exc()

class BidService:
    @staticmethod
    def place_bid(auction_id, user_id, amount, username=None):
        """Realiza um lance em um leilão"""
        # Recupera dados do leilão
        auction_data = AuctionService.get_auction(auction_id)
        if not auction_data:
            return None, "Auction not found"
        
        # Verifica se o leilão está ativo
        if auction_data.get('active', 'true') != 'true':
            return None, "Auction is closed"
        
        # Verifica se o tempo do leilão expirou
        try:
            end_time_str = auction_data['end_time']
            if 'Z' in end_time_str:
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            else:
                end_time = datetime.fromisoformat(end_time_str)
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)
            
            current_time = datetime.now(timezone.utc)
            
            if current_time >= end_time:
                redis_client.close_auction(auction_id)
                return None, "Auction has ended"
        except Exception as e:
            print(f"Error checking auction time: {e}")
            return None, "Error checking auction status"
        
        current_price = float(auction_data.get('current_price', 0))
        starting_price = float(auction_data.get('starting_price', 0))
        
        # Validação do lance
        if amount <= current_price:
            return None, f"Bid must be higher than current price (${current_price})"
        
        # Incremento mínimo de 5% sobre o lance atual
        min_increment = current_price * 1.05
        if amount < min_increment:
            return None, f"Minimum bid is ${min_increment:.2f}"
        
        # Verifica se o usuário não é o dono do leilão
        if str(user_id) == str(auction_data.get('owner_id')):
            return None, "You cannot bid on your own auction"
        
        # Cria o lance
        bid = Bid(
            auction_id=auction_id,
            user_id=user_id,
            amount=amount,
            username=username
        )
        
        # Salva o lance
        redis_client.add_bid_to_auction(auction_id, bid.to_dict())

        try:
            redis_client.get_connection().hset(f"auction:{auction_id}", 'current_winner', username)
            redis_client.get_connection().hset(f"auction:{auction_id}", 'current_winner_id', user_id)
            print(f"Updated winner for auction {auction_id}: {username} ({user_id})")
        except Exception as e:
            print(f"Error updating winner: {e}")
        
        # Publica notificação em tempo real
        redis_client.publish_message(
            f"auction:{auction_id}",
            {
                'type': 'new_bid',
                'bid': bid.to_dict(),
                'auction_id': auction_id,
                'current_price': amount,
                'winner': username,  # Adiciona o vencedor na notificação
                'winner_id': user_id
            }
        )
        
        return bid, None
    
    @staticmethod
    def get_auction_bids(auction_id, limit=20):
        """Recupera histórico de lances de um leilão"""
        return redis_client.get_auction_bids(auction_id, limit)