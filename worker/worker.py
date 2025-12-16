"""
Worker de IA para processamento de leilões finalizados.
Escuta eventos do Redis Pub/Sub e executa ações automatizadas.
"""
import os
import json
import time
import redis
from datetime import datetime

from ai_agent import AIAgent
from notifications import NotificationService


class AuctionWorker:
    """Worker que processa leilões finalizados."""
    
    CHANNEL = "leiloes_finalizados"
    
    def __init__(self):
        self.redis_host = os.getenv('REDIS_HOST', 'redis')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        
        print(f"🔧 Configurando conexão Redis: {self.redis_host}:{self.redis_port}")
        
        self.redis = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            decode_responses=True
        )
        self.pubsub = self.redis.pubsub()
        self.ai_agent = AIAgent()
        self.notifications = NotificationService()
        
    def wait_for_redis(self, max_retries=30, delay=2):
        """Aguarda conexão com Redis."""
        for i in range(max_retries):
            try:
                if self.redis.ping():
                    print(f"✅ Conectado ao Redis em {self.redis_host}:{self.redis_port}")
                    return True
            except redis.ConnectionError:
                print(f"⏳ Aguardando Redis... ({i+1}/{max_retries})")
                time.sleep(delay)
        raise Exception("❌ Não foi possível conectar ao Redis")
    
    def subscribe(self):
        """Inscreve-se no canal de leilões finalizados."""
        self.pubsub.subscribe(self.CHANNEL)
        print(f"📡 Inscrito no canal: {self.CHANNEL}")
    
    def process_auction_ended(self, auction_data: dict):
        """Processa um leilão finalizado."""
        try:
            auction = auction_data.get('auction', {})
            auction_id = auction.get('auction_id', 'N/A')
            
            print(f"\n{'='*50}")
            print(f"🔔 Leilão Finalizado: {auction.get('title', 'N/A')}")
            print(f"   ID: {auction_id}")
            print(f"   Vencedor: {auction.get('winner_name', 'Nenhum')}")
            print(f"   Valor Final: R$ {auction.get('current_price', 0):.2f}")
            print(f"{'='*50}\n")
            
            # Verifica se houve vencedor
            winner_email = 'navesmesajoao@gmail.com'
            
            # 1. Gerar relatório do leilão usando IA
            print("📝 Gerando relatório do leilão...")
            report = self.ai_agent.generate_auction_report(auction)
            print(f"   Relatório gerado: {len(report)} caracteres")
            
            # 2. Gerar e-mail para o vencedor
            print("✉️ Gerando e-mail para o vencedor...")
            email_content = self.ai_agent.generate_winner_email(auction)
            
            # 3. Enviar e-mail
            print(f"📧 Enviando e-mail para {winner_email}...")
            email_sent = self.notifications.send_email(
                to_email=winner_email,
                subject=f"Parabéns! Você venceu o leilão: {auction.get('title')}",
                body=email_content
            )
            print(f"   E-mail: {'✅ Enviado' if email_sent else '❌ Falhou'}")
            
            # 4. Gerar post para Discord
            print("💬 Gerando post para Discord...")
            discord_content = self.ai_agent.generate_discord_post(auction)
            
            # 5. Enviar para Discord
            print("🎮 Postando no Discord...")
            discord_sent = self.notifications.send_discord_message(discord_content)
            print(f"   Discord: {'✅ Enviado' if discord_sent else '❌ Falhou'}")
            
            print(f"\n✅ Processamento do leilão {auction_id} concluído!\n")
            
        except Exception as e:
            print(f"❌ Erro ao processar leilão: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """Loop principal do worker."""
        print("🚀 Iniciando AI Worker para Leilões...")
        print(f"   Python executando de: {os.getcwd()}")
        
        self.wait_for_redis()
        self.subscribe()
        
        print("👂 Aguardando eventos de leilões finalizados...\n")
        
        # Loop infinito para escutar mensagens
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    if data.get('type') == 'auction_ended':
                        self.process_auction_ended(data)
                except json.JSONDecodeError as e:
                    print(f"⚠️ Erro ao decodificar mensagem: {e}")
                except Exception as e:
                    print(f"❌ Erro ao processar mensagem: {e}")
                    import traceback
                    traceback.print_exc()


if __name__ == '__main__':
    worker = AuctionWorker()
    worker.run()