# Auction K8s Agents

Projeto desenvolvido para a disciplina **Sistemas Distribuídos (2025/2)**  
**Universidade Federal de São Carlos – Campus Sorocaba (UFSCar Sorocaba)**

---

## Descrição Geral

Este projeto implementa um sistema distribuído para gerenciamento de leilões, utilizando uma arquitetura orientada a eventos e orquestração via Kubernetes.

O sistema é composto por uma aplicação web para controle de leilões, um serviço de mensageria e um worker de automação com uso de Inteligência Artificial. A comunicação entre os componentes ocorre de forma assíncrona, permitindo desacoplamento, escalabilidade e processamento contínuo.

O objetivo principal é demonstrar, de forma prática, conceitos fundamentais de Sistemas Distribuídos, como:
- comunicação assíncrona
- processamento baseado em eventos
- separação de responsabilidades
- orquestração de serviços
- tolerância a falhas e escalabilidade

---

## Arquitetura do Sistema

O sistema é dividido nos seguintes componentes:

### 1. Aplicação Flask (Auction API)
- Fornece uma interface web simples e uma API REST
- Gerencia leilões (criação, atualização e finalização)
- Ao finalizar um leilão, publica um evento no Redis utilizando Pub/Sub

### 2. Redis
- Atua como broker de mensagens
- Utilizado para comunicação assíncrona entre a API e o worker
- Canal principal: `leiloes_finalizados`

### 3. AI Worker
- Serviço contínuo (worker)
- Inscrito no canal Redis de leilões finalizados
- Ao receber um evento:
  - Gera um relatório do leilão usando IA
  - Gera e envia um e-mail ao vencedor
  - Publica uma mensagem com o resultado em um canal do Discord

Todos os serviços são executados em containers Docker e gerenciados via Kubernetes.

---

## Tecnologias Utilizadas

- Python 3
- Flask
- Redis
- Docker
- Kubernetes (Kind ou Minikube)
- Redis Pub/Sub
- APIs de LLM (configuráveis via variáveis de ambiente)

---

## Estrutura do Projeto
```text
.
├── app/                    # Aplicação Flask (API e frontend)
│   ├── routes.py
│   ├── services.py
│   ├── redis_client.py
│   └── static/
├── worker/                 # Worker de automação com IA
│   ├── worker.py
│   ├── ai_agent.py
│   ├── notifications.py
│   ├── Dockerfile
│   └── requirements.txt
├── k8s/                    # Manifests Kubernetes
│   ├── namespace.yaml
│   ├── flask-deployment.yaml
│   ├── flask-service.yaml
│   ├── redis.yaml
│   ├── worker-deployment.yaml
│   ├── worker-secrets.yaml
│   └── hpa.yaml
├── Dockerfile              # Imagem da aplicação Flask
├── requirements.txt
└── README.md
```

---

## Execução com Kubernetes

### Pré-requisitos

* Docker
* kubectl
* Cluster Kubernetes local (Kind ou Minikube)

---

### 1. Criação do cluster (exemplo com Kind)

```bash
kind create cluster --config kind-config.yaml
```

---

### 2. Build das imagens Docker

```bash
docker build -t auction-flask:latest .
docker build -t auction-ai-worker:latest ./worker
```

> Em ambientes locais com Kind, as imagens devem existir no daemon Docker local.

---

### 3. Criação do namespace e serviços base

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/redis.yaml
```

---

### 4. Configuração de secrets

O worker utiliza secrets para armazenar:

* credenciais de e-mail
* webhook do Discord
* chave da API de IA

Essas informações devem ser definidas no arquivo:

```text
k8s/worker-secrets.yaml
```

Aplicação dos secrets:

```bash
kubectl apply -f k8s/worker-secrets.yaml
```

---

### 5. Deploy da aplicação e do worker

```bash
kubectl apply -f k8s/flask-deployment.yaml
kubectl apply -f k8s/flask-service.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/hpa.yaml
```

---

## Acesso à Aplicação Web

A aplicação Flask é exposta via **NodePort**.

Para verificar a porta:

```bash
kubectl get svc -n auction
```

Acesso pelo navegador:

```text
http://localhost:30080
```

---

