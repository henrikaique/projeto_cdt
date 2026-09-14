import os
import sqlite3
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError

load_dotenv()

DB_NAME = "chat_memory.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mensagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chave TEXT UNIQUE NOT NULL,
                valor TEXT NOT NULL
            )
        ''')
        conn.commit()

def salvar_mensagem(session_id: str, sender: str, content: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO mensagens (session_id, sender, content) VALUES (?, ?, ?)",
            (session_id, sender, content)
        )
        conn.commit()

def buscar_memorias_globais() -> str:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chave, valor FROM memorias")
        rows = cursor.fetchall()
        if not rows:
            return "Nenhuma memória prévia salva."
        return "\n".join([f"- {chave}: {valor}" for chave, valor in rows])

def salvar_memoria_global(chave: str, valor: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO memorias (chave, valor) VALUES (?, ?)
            ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor
        ''', (chave, valor))
        conn.commit()


init_db()
cliente = genai.Client()

SESSION_ID = "chat_sessao_001"
memorias_contexto = buscar_memorias_globais()

system_instruction = f"""
Você é um assistente virtual inteligente e prestativo.

[MEMÓRIAS DE LONGO PRAZO DO USUÁRIO]:
{memorias_contexto}

Use essas memórias para personalizar suas respostas sempre que relevante.
"""

# Configuração do modelo mantida estritamente para gemini-3.6-flash
chat = cliente.chats.create(
    model="gemini-3.6-flash",
    config=types.GenerateContentConfig(
        system_instruction=system_instruction
    )
)

print(f"Chatbot iniciado com modelo gemini-3.6-flash (Sessão: {SESSION_ID}).")
print("Digite 'sair' para encerrar.\n" + "-"*40)

while True:
    prompt_usuario = input("\nVocê: ").strip()
    
    if prompt_usuario.lower() == "sair":
        print("Encerrando chat...")
        break
        
    if not prompt_usuario:
        continue

    salvar_mensagem(SESSION_ID, "usuario", prompt_usuario)

    if prompt_usuario.startswith("/lembrar "):
        try:
            comando = prompt_usuario.replace("/lembrar ", "")
            chave, valor = comando.split("=", 1)
            salvar_memoria_global(chave.strip(), valor.strip())
            print(f"[Sistema]: Fato '{chave.strip()}' salvo na memória!")
            continue
        except ValueError:
            print("[Sistema]: Formato inválido. Use: /lembrar chave=valor")
            continue

    # Tentativa de envio com recuperação de cota (Retry Loop)
    sucesso = False
    tentativas = 0
    
    while not sucesso and tentativas < 3:
        try:
            resposta = chat.send_message(prompt_usuario)
            salvar_mensagem(SESSION_ID, "gemini", resposta.text)
            print(f"\nGemini: {resposta.text}")
            sucesso = True
        except ClientError as e:
            if "RESOURCE_EXHAUSTED" in str(e):
                tentativas += 1
                tempo_espera = 5  # Aguarda 5 segundos antes de tentar novamente
                print(f"\n[Aviso]: Cota momentânea excedida. Aguardando {tempo_espera}s para tentar novamente ({tentativas}/3)...")
                time.sleep(tempo_espera)
            else:
                print(f"\n[Erro na API]: {e}")
                break

'''
### O que mudou:
1. **Permanência do `gemini-3.6-flash`**: O modelo selecionado permanece como o principal da aplicação.
2. **Sistema de Retentativas (`time.sleep`)**: Caso a API retorne `RESOURCE_EXHAUSTED` (Erro 429), o script não trava. Ele aguarda 5 segundos até que a cota seja reabastecida pelo servidor do Google AI Studio e realiza até 3 tentativas de envio automaticamente.

<ElicitationsGroup message="Como deseja continuar a evolução do seu projeto?">
  <Elicitation label="Configurar o faturamento Pay-As-You-Go no Google AI Studio para remover limites" query="Como ativar a cobrança por uso (Pay-As-You-Go) na API do Gemini para não ter limites de requisições por minuto?"/>
  <Elicitation label="Recarregar o histórico anterior da tabela de SQL na sessão de chat" query="Como ler as últimas mensagens da tabela de SQL ao iniciar o script para o Gemini lembrar da conversa anterior?"/>
</ElicitationsGroup>
'''

