"""
===============================================================================
PROJETO: Agente de Inteligência Artificial "SKY"
===============================================================================
Descrição:
    Este script cria a IA chamada SKY. Ele lê a chave de API diretamente
    da variável 'SKY' do ficheiro .env e conecta-se ao Google Gemini.
===============================================================================
"""

import os
import sys
from dotenv import load_dotenv
from google import genai

# 1. Carrega as variáveis de ambiente a partir do ficheiro .env
load_dotenv()

# =============================================================================
# CLASSE DO AGENTE DE IA "SKY"
# =============================================================================

class AgenteSky:
    """
    Classe responsável por gerir a identidade e as respostas da IA SKY.
    """

    def __init__(self):
        """
        Inicializa o agente SKY e lê a chave guardada na variável 'SKY' do .env.
        """
        # Procura exatamente pela variável SKY no ficheiro .env
        self.api_key = os.getenv("SKY")

        # Mensagem de ajuda caso a variável SKY não seja encontrada
        if not self.api_key:
            print("\n❌ [ERRO] A variável 'SKY' não foi encontrada no teu ficheiro .env!")
            print("👉 Abre o ficheiro .env e garante que está escrito: SKY=tua_chave_aqui\n")
            sys.exit(1)

        # Conecta ao serviço do Google Gemini usando a chave lida da variável SKY
        self.cliente = genai.Client(api_key=self.api_key)
        self.nome = "SKY"
        print(f"🤖 [IA {self.nome}] Agente SKY inicializado com sucesso e pronto!")

    def responder(self, mensagem_usuario: str) -> str:
        """
        Envia a mensagem do utilizador para a IA Gemini com a personalidade da SKY.

        Parâmetros:
            mensagem_usuario (str): A pergunta ou mensagem enviada.

        Retorna:
            str: A resposta gerada pela SKY.
        """
        print(f"\n📩 [Você -> {self.nome}]: {mensagem_usuario}")

        # Instrução do sistema que define a identidade da SKY
        prompt_sistema = f"""
        Você é a SKY, uma Inteligência Artificial assistente virtual prestativa, educada e inteligente.
        Sempre que perguntarem o seu nome, identifique-se orgulhosamente como SKY.
        Responda à seguinte solicitação de forma clara e atenciosa:

        Solicitação: "{mensagem_usuario}"
        """

        # Envia a solicitação para o modelo Gemini 2.5 Flash
        resposta = self.cliente.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_sistema
        )

        print(f"✨ [{self.nome}]: {resposta.text}\n")
        return resposta.text


# =============================================================================
# EXECUÇÃO DA IA SKY
# =============================================================================

if __name__ == "__main__":
    # Instancia a IA SKY
    sky = AgenteSky()

    # Pergunta de teste para verificar se a SKY responde
    sky.responder("Olá! Quem és tu e como podes ajudar-me?")