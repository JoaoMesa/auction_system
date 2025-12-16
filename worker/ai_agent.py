"""
Agente de IA para geração de conteúdo automatizado.
Suporta Google Generative AI (gemini) e OpenAI. Se nenhum provider
estiver configurado, cai em modo simulado (fallback).
"""
import os
import traceback
from typing import Optional

try:
    import google.generativeai as genai  # pip install google-generativeai
    HAS_GOOGLE_AI = True
except Exception:
    genai = None
    HAS_GOOGLE_AI = False

try:
    import openai  # pip install openai
    HAS_OPENAI = True
except Exception:
    openai = None
    HAS_OPENAI = False


class AIAgent:
    def __init__(self):
        self.llm_provider = os.getenv("LLM_PROVIDER", "google").lower()
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.google_model = os.getenv("LLM_GOOGLE_MODEL", "gemini-2.5-flash")
        self.openai_model = os.getenv("LLM_OPENAI_MODEL", "gpt-3.5-turbo")

        self._client = None
        self._setup_client()

    def _setup_client(self):
        """Configura o client do provider escolhido, se possível."""
        try:
            if self.llm_provider == "google" and HAS_GOOGLE_AI:
                if self.api_key:
                    genai.configure(api_key=self.api_key)
                    # model object is optional; we'll call generative API functions dynamically
                    self._client = "google"
                    print(f"✅ Google Generative AI configurado (model={self.google_model})")
                else:
                    print("⚠️ LLM_API_KEY não configurada para Google; usando simulação.")
                    self._client = None
            elif self.llm_provider == "openai" and HAS_OPENAI:
                if self.api_key:
                    # compatibilidade com versões: use openai.api_key se importou pacote openai
                    try:
                        openai.api_key = self.api_key
                        self._client = "openai"
                        print(f"✅ OpenAI configurada (model={self.openai_model})")
                    except Exception as e:
                        print(f"⚠️ Falha ao configurar OpenAI: {e}")
                        self._client = None
                else:
                    print("⚠️ LLM_API_KEY não configurada para OpenAI; usando simulação.")
                    self._client = None
            else:
                print(f"⚠️ Provider '{self.llm_provider}' não disponível. Usando modo simulado.")
                self._client = None
        except Exception as e:
            print("⚠️ Erro ao configurar LLM client:", e)
            traceback.print_exc()
            self._client = None

    def _call_llm(self, prompt: str, temperature: float = 0.7, max_tokens: int = 512) -> str:
        """Chama o LLM configurado e retorna texto. Em caso de erro, usa simulação."""
        try:
            if self._client == "google" and HAS_GOOGLE_AI:
                # Exemplo genérico: usar genai para gerar texto — APIs podem variar entre versões
                try:
                    response = genai.generate_text(model=self.google_model, prompt=prompt, temperature=temperature)
                    # tentativa de extrair texto em várias possíveis chaves
                    text = ""
                    if isinstance(response, dict):
                        # algumas versões retornam {'candidates': [{'content': '...'}], ...}
                        if "candidates" in response and response["candidates"]:
                            text = response["candidates"][0].get("content", "")
                        else:
                            text = str(response)
                    else:
                        text = getattr(response, "text", str(response))
                    return text
                except Exception:
                    # fallback para outra forma
                    try:
                        # antiga interface: model.generate_content
                        model = genai.GenerativeModel(self.google_model)
                        resp = model.generate_content(prompt)
                        return getattr(resp, "text", str(resp))
                    except Exception as e:
                        print("⚠️ Erro Google AI (fallback):", e)
                        traceback.print_exc()
                        return self._simulate_response(prompt)
            elif self._client == "openai" and HAS_OPENAI:
                try:
                    # usa ChatCompletion (API clássica) para máxima compatibilidade
                    resp = openai.ChatCompletion.create(
                        model=self.openai_model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    # extrai texto
                    if resp and "choices" in resp and len(resp["choices"]) > 0:
                        choice = resp["choices"][0]
                        # algumas versões diferem na chamada, por isso robustez
                        if "message" in choice and "content" in choice["message"]:
                            return choice["message"]["content"]
                        elif "text" in choice:
                            return choice["text"]
                    return str(resp)
                except Exception as e:
                    print("⚠️ Erro OpenAI:", e)
                    traceback.print_exc()
                    return self._simulate_response(prompt)
            else:
                return self._simulate_response(prompt)
        except Exception as e:
            print("⚠️ Erro geral ao chamar LLM:", e)
            traceback.print_exc()
            return self._simulate_response(prompt)

    def _simulate_response(self, prompt: str) -> str:
        """Resposta simulada (fallback) — mantém sistema funcional se LLM ausente."""
        pl = prompt.lower()
        if "relatório" in pl or "resumo" in pl:
            return "[SIMULAÇÃO] Relatório do leilão gerado com sucesso."
        if "e-mail" in pl or "email" in pl:
            return "[SIMULAÇÃO] E-mail de parabenização gerado."
        if "discord" in pl or "post" in pl:
            return "[SIMULAÇÃO] Post para Discord gerado."
        return "[SIMULAÇÃO] Resposta gerada pelo agente de IA."

    # ---------- APIs públicas -----------
    def generate_auction_report(self, auction: dict) -> str:
        """Gera um relatório completo do leilão finalizado."""
        prompt = f"""Baseado no resultado do leilão abaixo, gere um relatório bem completo do leilão,
destacando o item, valor final e número de lances.

Dados do Leilão:
- Título: {auction.get('title', 'N/A')}
- Descrição: {auction.get('description', 'N/A')}
- Preço Inicial: R$ {float(auction.get('start_price', 0)):.2f}
- Valor Final: R$ {float(auction.get('current_price', 0)):.2f}
- Vencedor: {auction.get('winner_name', 'Nenhum')}
- E-mail do Vencedor: {auction.get('winner_email', 'N/A')}
- Total de Lances: {len(auction.get('bids', []) or [])}
- Data de Criação: {auction.get('created_at', 'N/A')}
- Data de Término: {auction.get('end_time', 'N/A')}

Gere um relatório profissional e detalhado em português brasileiro."""
        return self._call_llm(prompt)

    def generate_winner_email(self, auction: dict) -> str:
        """Gera o corpo do e-mail para o vencedor."""
        winner_name = auction.get("winner_name", "Participante")
        item_name = auction.get("title", "Item")
        final_value = float(auction.get("current_price", 0))
        prompt = f"""Escreva APENAS o corpo do e-mail, sem nenhuma introdução ou explicação.
Comece diretamente com a saudação ao vencedor.

E-mail parabenizando {winner_name} pela vitória no leilão do item \"{item_name}\" pelo valor de R$ {final_value:.2f}.

O e-mail deve:
1. Parabenizar o vencedor de forma calorosa
2. Confirmar os detalhes da compra (item e valor)
3. Informar os próximos passos para pagamento
4. Agradecer pela participação na plataforma
5. Incluir uma assinatura da equipe Lance Certo

Escreva em português brasileiro, de forma profissional mas amigável.
Resposta (apenas o e-mail, sem introdução):"""
        return self._call_llm(prompt)

    def generate_discord_post(self, auction: dict) -> str:
        """Gera post para o canal do Discord."""
        item_name = auction.get("title", "Item")
        final_value = float(auction.get("current_price", 0))
        winner_name = auction.get("winner_name", "Participante")
        total_bids = len(auction.get("bids", []) or [])
        prompt = f"""Escreva APENAS o post para Discord, sem nenhuma introdução ou explicação.
Comece diretamente com o anúncio usando emojis.

Post para o canal #resultados-leiloes anunciando que o item \"{item_name}\" foi arrematado por R$ {final_value:.2f} pelo vencedor {winner_name}.

O post deve:
1. Anunciar o resultado do leilão
2. Mencionar o item, valor final e vencedor
3. Incluir quantos lances foram feitos ({total_bids} lances)
4. Parabenizar o vencedor
5. Convidar outros a participarem dos próximos leilões

Mantenha o tom divertido e engajante, típico de comunidades no Discord.
Escreva em português brasileiro.
Resposta (apenas o post, sem introdução):"""
        return self._call_llm(prompt)
