"""
===============================================================================
PROJETO: Automação Sky + IA Gemini + Banco de Dados SQL
===============================================================================
Descrição:
    Script de automação web que lê chamados na plataforma Sky, processa as
    respostas com o Google Gemini e armazena todo o histórico em uma base
    de dados SQL local (SQLite).
"""

import asyncio
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from google import genai

# Carrega variáveis do ficheiro .env (caso utilizado)
load_dotenv()

# =============================================================================
# CONFIGURAÇÕES E VARIÁVEIS AJUSTÁVEIS
# =============================================================================

# Chave da API do Google Gemini
CHAVE_API_GEMINI = os.getenv("SKY_API_KEY", "AQ.Ab8RN6LqGx2uu7vxIZGxrwVJhEeAO0dL5rnaQvzoJ4unabXHWw")

# Configurações do Banco de Dados SQL
NOME_BANCO_DADOS = "historico_atendimentos.db"

# Dados da Plataforma Sky
URL_PLATAFORMA_SKY = "https://exemplo-sky.com"


# =============================================================================
# MÓDULO 1: BANCO DE DADOS SQL (SQLITE)
# =============================================================================

def inicializar_banco_dados():
    """
    Cria a conexão com o banco de dados SQL e garante que a tabela
    de atendimentos existe.
    """
    print("💾 [SQL] Inicializando a base de dados SQL...")
    
    # Conecta ao arquivo de banco de dados (é criado automaticamente se não existir)
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    cursor = conexao.cursor()
    
    # Comando DDL em SQL para criar a tabela
    comando_sql_criar_tabela = """
    CREATE TABLE IF NOT EXISTS atendimentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora TEXT NOT NULL,
        solicitacao_cliente TEXT NOT NULL,
        resposta_ia TEXT NOT NULL,
        status TEXT NOT NULL
    );
    """
    
    cursor.execute(comando_sql_criar_tabela)
    conexao.commit()
    conexao.close()
    print("✅ [SQL] Tabela 'atendimentos' verificada e pronta para uso!")


def salvar_atendimento_sql(solicitacao: str, resposta: str, status: str = "Concluído"):
    """
    Insere um registro de atendimento na tabela SQL.

    Parâmetros:
        solicitacao (str): Texto enviado pelo cliente.
        resposta (str): Texto gerado pela IA.
        status (str): Estado final da operação (ex: Concluído).
    """
    print("💾 [SQL] Salvando registro de atendimento no banco...")
    
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    cursor = conexao.cursor()
    
    # Data e hora atual em formato legível
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Comando DML em SQL para inserir dados
    comando_sql_inserir = """
    INSERT INTO atendimentos (data_hora, solicitacao_cliente, resposta_ia, status)
    VALUES (?, ?, ?, ?);
    """
    
    cursor.execute(comando_sql_inserir, (data_atual, solicitacao, resposta, status))
    conexao.commit()
    conexao.close()
    print("✅ [SQL] Atendimento gravado com sucesso no banco de dados!")


# =============================================================================
# MÓDULO 2: AGENTE DE INTELIGÊNCIA ARTIFICIAL
# =============================================================================

def consultar_agente_ia(mensagem_cliente: str) -> str:
    """
    Envia a solicitação lida na Sky para o Google Gemini e devolve a resposta.
    """
    print("🤖 [IA] Conectando ao serviço Google Gemini...")
    cliente = genai.Client(api_key=CHAVE_API_GEMINI)

    prompt = f"""
    Você é um assistente virtual de atendimento da plataforma Sky.
    Responda à seguinte solicitação de maneira clara, educada e profissional:

    Solicitação do Cliente: "{mensagem_cliente}"
    """

    resposta = cliente.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    print("✅ [IA] Resposta gerada com sucesso!")
    return resposta.text


# =============================================================================
# MÓDULO 3: AUTOMAÇÃO WEB (PLAYWRIGHT)
# =============================================================================

async def executar_automacao_sky():
    """
    Controla a execução principal:
    1. Abre o navegador.
    2. Lê o pedido.
    3. Consulta a IA.
    4. Responde na plataforma.
    5. Salva a operação no Banco SQL.
    """
    print("🌐 [Navegador] Iniciando automação com Playwright...")

    async with async_playwright() as p:
        navegador = await p.chromium.launch(headless=False)
        pagina = await navegador.new_page()

        print(f"🔗 [Navegador] Acessando {URL_PLATAFORMA_SKY}...")
        await pagina.goto(URL_PLATAFORMA_SKY)
        await pagina.wait_for_timeout(2000)

        # Simulação de leitura do pedido no site da Sky
        texto_pedido = "Olá, gostaria de verificar a fatura do mês atual."
        print(f"📥 [Leitura] Pedido lido: '{texto_pedido}'")

        # Processamento via IA
        resposta_ia = consultar_agente_ia(texto_pedido)

        # Registro no Banco de Dados SQL
        salvar_atendimento_sql(
            solicitacao=texto_pedido,
            resposta=resposta_ia,
            status="Processado com Sucesso"
        )

        # Captura de tela para documentação
        await pagina.screenshot(path="comprovativo_automacao.png")
        await navegador.close()
        print("🎉 [Sucesso] Processo completo finalizado!")


# =============================================================================
# PONTO DE ENTRADA DO PROGRAMA
# =============================================================================

if __name__ == "__main__":
    # 1. Garante que o banco SQL e as tabelas estão criados
    inicializar_banco_dados()
    
    # 2. Executa a automação principal
    asyncio.run(executar_automacao_sky())