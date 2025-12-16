from app import create_app
import threading
import time
import os

app = create_app()

def start_background_tasks():
    """Inicia tarefas em background apenas no primeiro pod"""
    from app.services import AuctionService
    
    # Usar variável de ambiente do pod para identificar instância principal
    pod_name = os.environ.get('POD_NAME', 'unknown')
    
    # Apenas o primeiro pod (por nome) executa tarefas de background
    # Isso evita duplicação de tarefas em múltiplas réplicas
    if pod_name.endswith('-0') or 'unknown' in pod_name:
        print(f"Pod {pod_name} is designated for background tasks")
        
        def check_expired_auctions():
            print("Starting expired auctions checker...")
            while True:
                try:
                    print("Checking for expired auctions...")
                    AuctionService.close_expired_auctions()
                except Exception as e:
                    print(f"Error checking expired auctions: {e}")
                    import traceback
                    traceback.print_exc()
                time.sleep(60)
        
        thread = threading.Thread(target=check_expired_auctions, daemon=True)
        thread.start()
        print("Background tasks started")
    else:
        print(f"Pod {pod_name} skipping background tasks")

if __name__ == '__main__':
    start_background_tasks()
    print("Starting Flask server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)