// Configuração
const API_BASE = '/api';
let currentAuctionId = null;
let eventSource = null;

// Elementos DOM
const elements = {
    // Abas
    tabButtons: document.querySelectorAll('.tab-button'),
    tabPanes: document.querySelectorAll('.tab-pane'),
    
    // Status
    status: document.getElementById('status'),
    
    // Debug
    bidStream: document.getElementById('bid-stream'),
    
    // Create Auction
    createAuctionForm: document.getElementById('create-auction-form'),
    createAuctionBtn: document.getElementById('create-auction-btn'),
    createAuctionMessage: document.getElementById('create-auction-message'),
    
    // Bid Auction
    auctionsContainer: document.getElementById('auctions-container'),
    
    // Modal
    bidModal: document.getElementById('bid-modal'),
    closeModal: document.querySelector('.close-modal'),
    bidModalForm: document.getElementById('bid-modal-form'),
    placeBidModalBtn: document.getElementById('place-bid-modal-btn'),
    bidModalMessage: document.getElementById('bid-modal-message'),
    modalAuctionId: document.getElementById('modal-auction-id'),
    modalAuctionTitle: document.getElementById('modal-auction-title'),
    modalAuctionDescription: document.getElementById('modal-auction-description'),
    modalCurrentPrice: document.getElementById('modal-current-price'),
    modalTimeLeft: document.getElementById('modal-time-left'),
    bidderNameModal: document.getElementById('bidder-name-modal'),
    bidAmountModal: document.getElementById('bid-amount-modal'),
    bidderIdModal: document.getElementById('bidder-id-modal')
};

// ========== INICIALIZAÇÃO ==========
document.addEventListener('DOMContentLoaded', function() {
    console.log('Auction System initialized');
    
    // Configurar abas
    setupTabs();
    
    // Configurar modal
    setupModal();
    
    // Configurar formulários
    setupForms();
    
    // Carregar status inicial
    checkStatus();
    
    // Carregar leilões
    loadAuctions();
    
    // Configurar intervalos
    setInterval(checkStatus, 30000);
    setInterval(loadAuctions, 10000);
});

// ========== FUNÇÕES UTILITÁRIAS ==========
function showMessage(container, message, type = 'info') {
    if (!container) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = type;
    messageDiv.innerHTML = message;
    
    container.insertBefore(messageDiv, container.firstChild);
    
    // Remover automaticamente após 5 segundos
    if (type === 'success' || type === 'error') {
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.parentNode.removeChild(messageDiv);
            }
        }, 5000);
    }
}

function formatPrice(price) {
    return `$${parseFloat(price).toFixed(2)}`;
}

function formatTimeLeft(endTime) {
    const now = new Date();
    const end = new Date(endTime);
    const diff = end - now;
    
    if (diff <= 0) return 'Ended';
    
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
}

// ========== CONFIGURAÇÃO DE ABAS ==========
function setupTabs() {
    if (!elements.tabButtons) return;
    
    elements.tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');
            
            // Remover classe active de todos os botões e painéis
            elements.tabButtons.forEach(btn => btn.classList.remove('active'));
            elements.tabPanes.forEach(pane => pane.classList.remove('active'));
            
            // Adicionar classe active ao botão e painel clicado
            this.classList.add('active');
            document.getElementById(tabId).classList.add('active');
            
            // Se for a aba de debug, conectar ao stream do leilão atual (se houver)
            if (tabId === 'debug' && currentAuctionId) {
                connectToStream(currentAuctionId);
            }
        });
    });
}

// ========== CONFIGURAÇÃO DE MODAL ==========
function setupModal() {
    if (!elements.closeModal || !elements.bidModal) return;
    
    // Fechar modal quando clicar no X
    elements.closeModal.addEventListener('click', closeBidModal);
    
    // Fechar modal quando clicar fora dele
    window.addEventListener('click', function(event) {
        if (event.target === elements.bidModal) {
            closeBidModal();
        }
    });
    
    // Fechar com ESC
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeBidModal();
        }
    });
}

async function openBidModal(auctionId) {
    if (!elements.bidModal) return;
    
    console.log(`Opening bid modal for auction: ${auctionId}`);
    
    try {
        // Buscar dados atualizados do leilão
        const response = await fetch(`${API_BASE}/auctions/${auctionId}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch auction: ${response.status}`);
        }
        
        const data = await response.json();
        const auction = data.auction;
        
        if (!auction) {
            showMessage(elements.bidModalMessage, 'Auction not found', 'error');
            return;
        }
        
        const isActive = auction.active === 'true';
        if (!isActive) {
            showMessage(elements.bidModalMessage, 'This auction is closed', 'error');
            return;
        }
        
        // Preencher dados no modal
        elements.modalAuctionId.value = auctionId;
        elements.modalAuctionTitle.textContent = auction.title;
        elements.modalAuctionDescription.textContent = auction.description;
        elements.modalCurrentPrice.textContent = formatPrice(auction.current_price);
        elements.modalTimeLeft.textContent = formatTimeLeft(auction.end_time);
        
        // MOSTRAR VENCEDOR ATUAL
        const winnerElement = document.getElementById('modal-current-winner');
        if (winnerElement) {
            if (auction.current_winner && auction.current_winner.trim() !== '') {
                winnerElement.innerHTML = `<i class="fas fa-crown"></i> ${auction.current_winner}`;
                winnerElement.style.color = '#48bb78';
                winnerElement.style.fontWeight = 'bold';
            } else {
                winnerElement.textContent = 'No bids yet';
                winnerElement.style.color = '#a0aec0';
                winnerElement.style.fontWeight = 'normal';
            }
        }
        
        // Calcular lance mínimo (5% acima do preço atual)
        const minBid = parseFloat(auction.current_price) * 1.05;
        elements.bidAmountModal.value = minBid.toFixed(2);
        elements.bidAmountModal.min = minBid.toFixed(2);
        
        // Limpar campo de nome e focar nele
        elements.bidderNameModal.value = '';
        elements.bidModalMessage.innerHTML = '';
        
        // Mostrar modal
        elements.bidModal.style.display = 'block';
        console.log('Modal displayed');
        
        // Focar no campo de nome com delay para garantir que o modal está visível
        setTimeout(() => {
            elements.bidderNameModal.focus();
        }, 100);
        
    } catch (error) {
        console.error('Error opening bid modal:', error);
        showMessage(elements.bidModalMessage, `Error: ${error.message}`, 'error');
    }
}
function closeBidModal() {
    if (!elements.bidModal) return;
    elements.bidModal.style.display = 'none';
    console.log('Modal closed');
}

function setMinBid() {
    const minBid = parseFloat(elements.bidAmountModal.min);
    elements.bidAmountModal.value = minBid.toFixed(2);
}

// ========== VERIFICAÇÃO DE STATUS ==========
async function checkStatus() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        updateStatusDisplay(data);
    } catch (error) {
        console.error('Status check failed:', error);
        updateStatusDisplay({ status: 'error', redis_connected: false });
    }
}

function updateStatusDisplay(data) {
    if (!elements.status) return;
    
    const isHealthy = data.status === 'healthy' && data.redis_connected;
    const lastCheck = new Date().toLocaleTimeString();
    
    elements.status.innerHTML = `
        <div class="${isHealthy ? 'success' : 'error'}">
            <h3>System Status</h3>
            <p>
                <span class="status-indicator ${isHealthy ? 'status-online' : 'status-offline'}"></span>
                <strong>${isHealthy ? 'System Online' : 'System Issues'}</strong>
            </p>
            <p>Redis: ${data.redis_connected ? 'Connected ✅' : 'Disconnected ❌'}</p>
            <p>Last Check: ${lastCheck}</p>
        </div>
    `;
}

// ========== CARREGAR LEILÕES ==========
async function loadAuctions() {
    try {
        const response = await fetch(`${API_BASE}/auctions`);
        const data = await response.json();
        
        updateAuctionsDisplay(data.auctions || []);
    } catch (error) {
        console.error('Error loading auctions:', error);
        showMessage(elements.auctionsContainer, 'Error loading auctions', 'error');
    }
}
function updateAuctionsDisplay(auctions) {
    if (!elements.auctionsContainer) return;
    
    console.log('DEBUG - Updating auctions display with data:', auctions);
    
    if (!auctions || auctions.length === 0) {
        elements.auctionsContainer.innerHTML = `
            <div class="info">
                <p>No active auctions found. Create one to get started!</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="auctions-grid">';
    
    auctions.forEach(auction => {
        console.log('DEBUG - Processing auction:', {
            title: auction.title,
            current_winner: auction.current_winner,
            hasWinner: auction.current_winner && auction.current_winner.trim() !== ''
        });
        
        const isActive = auction.active === 'true';
        const timeLeft = formatTimeLeft(auction.end_time);
        const currentPrice = formatPrice(auction.current_price);
        const statusClass = isActive ? 'success' : 'error';
        const statusText = isActive ? 'Active' : 'Closed';
        const hasWinner = auction.current_winner && auction.current_winner.trim() !== '';
        
        html += `
            <div class="auction-card">
                <h3><i class="fas fa-gavel"></i> ${auction.title}</h3>
                <p>${auction.description.substring(0, 150)}${auction.description.length > 150 ? '...' : ''}</p>
                
                <span class="price-tag">${currentPrice}</span>
                
                <div class="auction-meta">
                    <div class="meta-item">
                        <span class="meta-label">Starting Price</span>
                        <span class="meta-value">${formatPrice(auction.starting_price)}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Bids</span>
                        <span class="meta-value">${auction.bid_count || 0}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Status</span>
                        <span class="meta-value ${statusClass}">${statusText}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Current Winner</span>
                        <span class="meta-value" style="color: ${hasWinner ? '#48bb78' : '#a0aec0'}; font-weight: ${hasWinner ? 'bold' : 'normal'};">
                            ${hasWinner ? 
                                `<i class="fas fa-crown" style="color: #f6e05e; margin-right: 5px;"></i>${auction.current_winner}` : 
                                'No bids yet'}
                        </span>
                    </div>
                </div>
                
                <div class="timer">${timeLeft}</div>
                
                ${isActive ? `
                    <button class="btn-bid" onclick="openBidModal('${auction.id}')">
                        <i class="fas fa-money-bill-wave"></i> Place Bid
                    </button>
                ` : `
                    <button class="btn-bid" disabled>
                        <i class="fas fa-ban"></i> Auction Closed
                    </button>
                `}
            </div>
        `;
    });
    
    html += '</div>';
    elements.auctionsContainer.innerHTML = html;
    
    console.log('DEBUG - HTML generated successfully');
}
// ========== STREAM EM TEMPO REAL ==========
function connectToStream(auctionId) {
    // Fechar conexão anterior
    if (eventSource) {
        eventSource.close();
    }
    
    if (!elements.bidStream) return;
    
    // Inicializar stream
    elements.bidStream.innerHTML = '<div class="info"><p>Connecting to real-time stream...</p></div>';
    
    eventSource = new EventSource(`${API_BASE}/auctions/${auctionId}/stream`);
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            handleStreamMessage(data);
        } catch (error) {
            console.error('Error parsing stream message:', error);
        }
    };
    
    eventSource.onerror = function(error) {
        console.error('EventSource error:', error);
        showMessage(elements.bidStream, 'Connection lost. Reconnecting...', 'error');
    };
}

function handleStreamMessage(data) {
    if (!elements.bidStream) return;
    
    let message = '';
    
    switch(data.type) {
        case 'new_bid':
            message = `
                <div class="stream-message">
                    🎯 <strong>${data.bid.username}</strong> placed a bid of 
                    <strong>${formatPrice(data.bid.amount)}</strong> on auction
                    <br>
                    <small>${new Date(data.bid.timestamp * 1000).toLocaleTimeString()}</small>
                </div>
            `;
            // Atualizar lista de leilões
            loadAuctions();
            break;
            
        case 'auction_ended':
        case 'auction_closed':
            message = `
                <div class="stream-message" style="border-left-color: #f56565;">
                    🔒 Auction ${data.auction_id} ${data.type === 'auction_ended' ? 'ended' : 'closed manually'}
                    ${data.final_price ? ` - Final Price: ${formatPrice(data.final_price)}` : ''}
                </div>
            `;
            loadAuctions();
            break;
            
        case 'connected':
            message = `
                <div class="stream-message" style="border-left-color: #4299e1;">
                    ✅ Connected to auction ${data.auction_id}
                </div>
            `;
            break;
            
        default:
            message = `<div class="stream-message">${JSON.stringify(data)}</div>`;
    }
    
    elements.bidStream.insertAdjacentHTML('afterbegin', message);
    
    // Limitar número de mensagens no stream
    const messages = elements.bidStream.querySelectorAll('.stream-message');
    if (messages.length > 20) {
        messages[messages.length - 1].remove();
    }
    
    // Auto-scroll para novas mensagens
    elements.bidStream.scrollTop = 0;
}

// ========== CONFIGURAÇÃO DE FORMULÁRIOS ==========
function setupForms() {
    // Formulário de criação de leilão
    if (elements.createAuctionForm) {
        elements.createAuctionForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (elements.createAuctionBtn) {
                elements.createAuctionBtn.disabled = true;
                elements.createAuctionBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
            }
            
            try {
                const formData = new FormData(this);
                const auctionData = {
                    title: formData.get('title'),
                    description: formData.get('description'),
                    starting_price: parseFloat(formData.get('starting_price')),
                    owner_id: formData.get('owner_id') || 'user_' + Date.now(),
                    duration_hours: parseInt(formData.get('duration_hours') || '24')
                };
                
                console.log('Sending auction data:', auctionData);
                
                const response = await fetch(`${API_BASE}/auctions`, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(auctionData)
                });
                
                console.log('Response status:', response.status);
                
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`Server returned ${response.status}: ${errorText}`);
                }
                
                const result = await response.json();
                console.log('Response JSON:', result);
                
                if (response.ok) {
                    showMessage(elements.createAuctionMessage, 
                        '<i class="fas fa-check-circle"></i> Auction created successfully!', 
                        'success');
                    
                    // Limpar formulário
                    this.reset();
                    document.getElementById('owner_id').value = 'user_' + Date.now();
                    document.getElementById('duration_hours').value = '24';
                    
                    // Atualizar lista de leilões
                    setTimeout(() => {
                        loadAuctions();
                    }, 1000);
                    
                    // Mudar para a aba de Bid
                    document.querySelector('[data-tab="bid"]').click();
                    
                } else {
                    showMessage(elements.createAuctionMessage, 
                        `<i class="fas fa-exclamation-circle"></i> Error: ${result.error || 'Unknown error'}`, 
                        'error');
                }
            } catch (error) {
                console.error('Error creating auction:', error);
                showMessage(elements.createAuctionMessage, 
                    `<i class="fas fa-exclamation-circle"></i> Error: ${error.message}`, 
                    'error');
            } finally {
                if (elements.createAuctionBtn) {
                    elements.createAuctionBtn.disabled = false;
                    elements.createAuctionBtn.innerHTML = '<i class="fas fa-rocket"></i> Create Auction';
                }
            }
        });
    }
    
    // Formulário de lance no modal
    if (elements.bidModalForm) {
    elements.bidModalForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const auctionId = elements.modalAuctionId.value;
        if (!auctionId) {
            showMessage(elements.bidModalMessage, 'No auction selected', 'error');
            return;
        }
        
        if (elements.placeBidModalBtn) {
            elements.placeBidModalBtn.disabled = true;
            elements.placeBidModalBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Placing Bid...';
        }
        
        try {
            // GERAR user_id AUTOMATICAMENTE baseado no nome
            const username = elements.bidderNameModal.value || 'Anonymous';
            // Remover espaços e caracteres especiais para criar um ID único
            const cleanName = username.replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_]/g, '');
            const userId = `${cleanName}_${Date.now()}`;
            
            const bidData = {
                user_id: userId,  // Gerado automaticamente
                amount: parseFloat(elements.bidAmountModal.value),
                username: username
            };
            
            console.log('Sending bid data:', bidData);
            
            const response = await fetch(`${API_BASE}/auctions/${auctionId}/bids`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(bidData)
            });
                
                console.log('Response status:', response.status);
                
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`Server returned ${response.status}: ${errorText}`);
                }
                
                const result = await response.json();
                console.log('Response JSON:', result);
                
                if (response.ok) {
                    showMessage(elements.bidModalMessage, 
                        '<i class="fas fa-check-circle"></i> Bid placed successfully!', 
                        'success');
                    
                    // Conectar ao stream na aba de Debug
                    currentAuctionId = auctionId;
                    connectToStream(auctionId);
                    
                    // Atualizar lista de leilões
                    setTimeout(() => {
                        loadAuctions();
                    }, 1000);
                    
                    // Fechar modal após 2 segundos
                    setTimeout(() => {
                        closeBidModal();
                    }, 2000);
                    
                } else {
                    showMessage(elements.bidModalMessage, 
                        `<i class="fas fa-exclamation-circle"></i> Error: ${result.error || 'Unknown error'}`, 
                        'error');
                }
            } catch (error) {
                console.error('Error placing bid:', error);
                showMessage(elements.bidModalMessage, 
                    `<i class="fas fa-exclamation-circle"></i> Error: ${error.message}`, 
                    'error');
            } finally {
                if (elements.placeBidModalBtn) {
                    elements.placeBidModalBtn.disabled = false;
                    elements.placeBidModalBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Place Bid';
                }
            }
        });
    }
}

// ========== FUNÇÕES GLOBAIS ==========
// Exportar funções para uso global
window.openBidModal = openBidModal;
window.closeBidModal = closeBidModal;
window.setMinBid = setMinBid;