#!/bin/bash

NAMESPACE="auction"
SERVICE_URL="http://localhost:30080"
REDIS_POD="redis-0"
WORKER_LABEL="app=ai-worker"

echo "========================================"
echo " Testes do Sistema - Auction K8s Agents "
echo " (com logs em tempo real)"
echo "========================================"
echo

# -------------------------------
# Teste 1: API REST
# -------------------------------
echo "[TESTE 1] Verificando se a API REST está acessível..."
echo

curl -s -o /dev/null -w "Status HTTP: %{http_code}\n" $SERVICE_URL

sleep 2
echo
echo "----------------------------------------"
echo

# -------------------------------
# Iniciando logs do worker
# -------------------------------
echo "[LOGS] Iniciando acompanhamento dos logs do worker..."
echo "Pressione CTRL+C ao final se desejar encerrar o streaming."
echo

kubectl logs -n $NAMESPACE -l $WORKER_LABEL -f &
LOGS_PID=$!

sleep 3

# -------------------------------
# Teste 2: Evento único
# -------------------------------
echo
echo "[TESTE 2] Publicando evento de leilão finalizado..."
echo

kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli PUBLISH leiloes_finalizados '{
  "type": "auction_ended",
  "auction": {
    "auction_id": "TEST-001",
    "title": "Leilão de Teste",
    "winner_name": "Usuário Teste",
    "winner_email": "joaomesa@estudante.ufscar.br",
    "current_price": 500.00
  }
}'

sleep 6
echo
echo "----------------------------------------"
echo

# -------------------------------
# Teste 3: Carga gradual
# -------------------------------
echo "[TESTE 3] Enviando múltiplos eventos com intervalo..."
echo

for i in 1 2 3
do
  echo "→ Publicando evento LOAD-$i"
  kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli PUBLISH leiloes_finalizados "{
    \"type\": \"auction_ended\",
    \"auction\": {
      \"auction_id\": \"LOAD-$i\",
      \"title\": \"Teste de Carga\",
      \"winner_name\": \"User\",
      \"winner_email\": \"joaomesa@estudante.ufscar.br\",
      \"current_price\": $((i * 100))
    }
  }"

  sleep 5
done

echo
echo "----------------------------------------"
echo

# -------------------------------
# Finalização
# -------------------------------
echo "[FINAL] Encerrando acompanhamento dos logs..."
kill $LOGS_PID 2>/dev/null

echo
echo "========================================"
echo " Testes finalizados"
echo "========================================"
