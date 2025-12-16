from flask import Blueprint, request, jsonify, Response, send_from_directory
from app.services import AuctionService, BidService
from app.redis_client import redis_client
from datetime import datetime, timedelta, timezone
import json
import traceback

main_bp = Blueprint('main', __name__)

# ========== ROTA DE DEBUG ==========
@main_bp.route('/api/debug/redis', methods=['GET'])
def debug_redis():
    """Endpoint para debug do Redis"""
    try:
        # Listar todas as chaves
        keys = redis_client.get_connection().keys("*")
        
        result = {
            'keys': keys,
            'active_auctions': list(redis_client.get_active_auctions()),
            'auctions_data': []
        }
        
        # Buscar dados de cada leilão
        for key in keys:
            if key.startswith('auction:') and not key.endswith(':bids'):
                auction_id = key.replace('auction:', '')
                data = redis_client.get_connection().hgetall(key)
                result['auctions_data'].append({
                    'key': key,
                    'id': auction_id,
                    'data': data
                })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== AUCTIONS ==========
@main_bp.route('/api/auctions', methods=['POST'])
def create_auction():
    """Cria um novo leilão"""
    print("\n=== CREATE AUCTION REQUEST ===")
    
    try:
        data = request.get_json()
        print(f"Received data: {data}")
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return jsonify({'error': 'Invalid JSON'}), 400
    
    # Validação
    required_fields = ['title', 'description', 'starting_price', 'owner_id']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        error_msg = f'Missing required fields: {", ".join(missing_fields)}'
        print(f"Validation error: {error_msg}")
        return jsonify({'error': error_msg}), 400
    
    # Define tempo de término padrão se não fornecido
    if 'end_time' not in data:
        duration_hours = int(data.get('duration_hours', 24))
        end_datetime = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        # Formato correto ISO com 'Z' no final (sem +00:00 antes do Z)
        end_time = end_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        data['end_time'] = end_time
        print(f"Generated end_time: {end_time}")
    
    try:
        # Cria o leilão
        auction, error = AuctionService.create_auction(
            title=data['title'],
            description=data['description'],
            starting_price=float(data['starting_price']),
            end_time=data['end_time'],
            owner_id=data['owner_id']
        )
        
        if error:
            print(f"Service error: {error}")
            return jsonify({'error': error}), 400
        
        print(f"Auction created successfully: {auction.id}")
        
        response_data = {
            'message': 'Auction created successfully',
            'auction': auction.to_dict()
        }
        
        print(f"Returning response: {response_data}")
        return jsonify(response_data), 201
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@main_bp.route('/api/auctions', methods=['GET'])
def get_auctions():
    """Lista todos os leilões ativos"""
    print("\n=== GET AUCTIONS REQUEST ===")
    
    try:
        auctions = AuctionService.get_active_auctions()
        print(f"Found {len(auctions)} auctions")
        
        return jsonify({
            'count': len(auctions),
            'auctions': auctions
        })
    except Exception as e:
        print(f"Error getting auctions: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/auctions/<auction_id>', methods=['GET'])
def get_auction(auction_id):
    """Obtém detalhes de um leilão específico"""
    print(f"\n=== GET AUCTION {auction_id} ===")
    
    try:
        auction = AuctionService.get_auction(auction_id)
        if not auction:
            return jsonify({'error': 'Auction not found'}), 404
        
        bids = BidService.get_auction_bids(auction_id)
        
        return jsonify({
            'auction': auction,
            'bids': bids
        })
    except Exception as e:
        print(f"Error getting auction: {e}")
        return jsonify({'error': str(e)}), 500

# ========== BIDS ==========
@main_bp.route('/api/auctions/<auction_id>/bids', methods=['POST'])
def place_bid(auction_id):
    """Realiza um lance em um leilão"""
    print(f"\n=== PLACE BID REQUEST for {auction_id} ===")
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    try:
        data = request.get_json()
        print(f"Bid data: {data}")
    except Exception as e:
        return jsonify({'error': f'Invalid JSON: {str(e)}'}), 400
    
    required_fields = ['user_id', 'amount']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
    
    try:
        bid, error = BidService.place_bid(
            auction_id=auction_id,
            user_id=data['user_id'],
            amount=float(data['amount']),
            username=data.get('username')
        )
        
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'message': 'Bid placed successfully',
            'bid': bid.to_dict()
        }), 201
        
    except Exception as e:
        print(f"Error placing bid: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/auctions/<auction_id>/bids', methods=['GET'])
def get_bids(auction_id):
    """Obtém histórico de lances de um leilão"""
    try:
        limit = request.args.get('limit', 20, type=int)
        bids = BidService.get_auction_bids(auction_id, limit)
        return jsonify({'bids': bids})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/auctions/<auction_id>/stream')
def stream_bids(auction_id):
    """Stream de eventos em tempo real para um leilão"""
    def event_stream():
        pubsub = redis_client.subscribe_to_channel(f"auction:{auction_id}")
        
        try:
            # Envia uma mensagem de conexão inicial
            yield f"data: {json.dumps({'type': 'connected', 'auction_id': auction_id})}\n\n"
            
            for message in pubsub.listen():
                if message['type'] == 'message':
                    yield f"data: {message['data']}\n\n"
        except Exception as e:
            print(f"Stream error: {e}")
        finally:
            pubsub.close()
    
    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

# ========== OUTRAS ROTAS ==========
@main_bp.route('/api/auctions/<auction_id>/close', methods=['POST'])
def close_auction(auction_id):
    """Fecha um leilão manualmente"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()
    
    if 'user_id' not in data:
        return jsonify({'error': 'Missing user_id'}), 400
    
    try:
        auction = AuctionService.get_auction(auction_id)
        
        if not auction:
            return jsonify({'error': 'Auction not found'}), 404
        
        # Verifica se o solicitante é o dono
        if str(data.get('user_id')) != str(auction.get('owner_id')):
            return jsonify({'error': 'Only the auction owner can close it'}), 403
        
        redis_client.close_auction(auction_id)
        
        return jsonify({'message': 'Auction closed successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== ROTAS DO FRONTEND ==========
@main_bp.route('/')
def index():
    return send_from_directory('static', 'index.html')

@main_bp.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)