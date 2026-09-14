"""
===============================================================================
PROJETO FINAL: IA "SKY" com Modelo Avançado (Llama 3.1 8B) e Memória Ativa
===============================================================================
Descrição:
    Este programa atualiza o modelo do Ollama para 'llama3.1:8b', garantindo
    português perfeito, raciocínio avançado e interpretação sem falhas da
    memória de longo prazo armazenada no SQLite.
===============================================================================
"""

import sys
import sqlite3
import hashlib
from datetime import datetime

# Validação e Importação da biblioteca Ollama
try:
    import ollama
except ImportError:
    print("\n❌ [ERRO DE BIBLIOTECA]")
    print("A biblioteca 'ollama' não está instalada no teu ambiente Python.")
    print("👉 Executa no terminal: pip install ollama\n")
    sys.exit(1)


# =============================================================================
# CONFIGURAÇÕES DO PROJETO (MODELO ATUALIZADO)
# =============================================================================
MODELO_AVANCADO_OLLAMA = "llama3.1:8b"  # Modelo mais inteligente e sem erros ortográficos
NOME_BANCO_DADOS = "historico_sky.db"
LIMITE_MENSAGENS_RECENTES = 8


# =============================================================================
# MÓDULO 1: BANCO DE DADOS SQLITE COM SENHAS E MEMÓRIA
# =============================================================================

def encriptar_senha(senha: str) -> str:
    """Converte a senha em texto limpo num HASH SHA-256 seguro."""
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()


def inicializar_banco_dados():
    """Cria as tabelas de usuários, conversas e memória resumida."""
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    cursor = conexao.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        data_hora TEXT NOT NULL,
        usuario_msg TEXT NOT NULL,
        resposta_sky TEXT NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memoria_resumida (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER UNIQUE NOT NULL,
        resumo TEXT NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    );
    """)

    conexao.commit()
    conexao.close()
    print("💾 [SQL] Banco de dados verificado e pronto!")


def autenticar_ou_cadastrar_usuario(nome_usuario: str, senha_digitada: str) -> tuple:
    """Valida as credenciais ou cadastra um novo usuário."""
    nome_limpo = nome_usuario.strip().title()
    senha_hash = encriptar_senha(senha_digitada.strip())

    if not nome_limpo or not senha_digitada.strip():
        return False, None, "Nome de usuário e senha não podem estar em branco."

    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    cursor = conexao.cursor()

    cursor.execute("SELECT id, senha_hash FROM usuarios WHERE nome = ?;", (nome_limpo,))
    usuario = cursor.fetchone()

    if usuario:
        usuario_id, hash_salvo = usuario
        if hash_salvo == senha_hash:
            conexao.close()
            return True, usuario_id, f"Bem-vindo(a) de volta, {nome_limpo}!"
        else:
            conexao.close()
            return False, None, "❌ Senha incorreta! Acesso negado."
    else:
        cursor.execute("INSERT INTO usuarios (nome, senha_hash) VALUES (?, ?);", (nome_limpo, senha_hash))
        usuario_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO memoria_resumida (usuario_id, resumo) VALUES (?, ?);",
            (usuario_id, "Nenhum fato registrado ainda.")
        )
        conexao.commit()
        conexao.close()
        return True, usuario_id, f"🎉 Novo usuário '{nome_limpo}' cadastrado com sucesso!"


def salvar_conversa_sql(usuario_id: int, usuario_msg: str, resposta_sky: str):
    """Guarda a conversa no banco associada ao ID do usuário."""
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    cursor = conexao.cursor()
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO conversas (usuario_id, data_hora, usuario_msg, resposta_sky)
    VALUES (?, ?, ?, ?);
    """, (usuario_id, data_atual, usuario_msg, resposta_sky))

    conexao.commit()
    conexao.close()


def obter_resumo_memoria(usuario_id: int) -> str:
    """Recupera os fatos gravados na memória apenas do usuário autenticado."""
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    cursor = conexao.cursor()
    cursor.execute("SELECT resumo FROM memoria_resumida WHERE usuario_id = ?;", (usuario_id,))
    resultado = cursor.fetchone()
    conexao.close()
    return resultado[0] if resultado else "Nenhum fato registrado ainda."


def atualizar_resumo_memoria(usuario_id: int, novo_resumo: str):
    """Atualiza a memória de longo prazo do usuário."""
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    cursor = conexao.cursor()
    cursor.execute("UPDATE memoria_resumida SET resumo = ? WHERE usuario_id = ?;", (novo_resumo, usuario_id))
    conexao.commit()
    conexao.close()


def obter_historico_recente_sql(usuario_id: int, limite: int = LIMITE_MENSAGENS_RECENTES) -> list:
    """Recupera o histórico recente de conversas do usuário."""
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    cursor = conexao.cursor()

    cursor.execute("""
    SELECT usuario_msg, resposta_sky FROM conversas 
    WHERE usuario_id = ?
    ORDER BY id DESC LIMIT ?;
    """, (usuario_id, limite))

    registos = cursor.fetchall()
    conexao.close()
    registos.reverse()

    historico_formatado = []
    for msg_user, msg_sky in registos:
        if msg_user.strip():
            historico_formatado.append({"role": "user", "content": msg_user})
        if msg_sky.strip():
            historico_formatado.append({"role": "assistant", "content": msg_sky})

    return historico_formatado


# =============================================================================
# MÓDULO 2: CLASSE DA IA "SKY" (MODELO AVANÇADO)
# =============================================================================

class AgenteSky:
    def __init__(self, modelo: str = MODELO_AVANCADO_OLLAMA):
        self.modelo = modelo
        self.nome = "SKY"

    def _obter_contexto_temporal(self) -> str:
        agora = datetime.now()
        dias_semana = {
            0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira",
            3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"
        }
        return f"{dias_semana[agora.weekday()]}, {agora.strftime('%d/%m/%Y às %H:%M:%S')}"

    def responder(self, usuario_id: int, nome_usuario: str, mensagem_usuario: str) -> str:
        """Gera a resposta da SKY usando o modelo avançado e a memória isolada."""
        self._extrair_e_guardar_fatos(usuario_id, mensagem_usuario)

        momento_atual = self._obter_contexto_temporal()
        resumo_fatos = obter_resumo_memoria(usuario_id)

        instrucao_sistema = {
            "role": "system",
            "content": (
                f"Você é a SKY, uma assistente virtual inteligente, simpática e altamente precisa.\n"
                f"Você está conversando com o usuário autenticado: {nome_usuario}.\n"
                f"Data e Hora atuais: {momento_atual}.\n\n"
                f"REGRAS DE MEMÓRIA E ATENDIMENTO:\n"
                f"1. Você possui acesso direto às memórias locais salvas sobre o usuário {nome_usuario}.\n"
                f"2. NUNCA diga que não se lembra de conversas passadas ou que não tem permissão para guardar fatos.\n"
                f"3. Sempre que o usuário perguntar o que você lembra sobre ele, apresente claramente os fatos salvos abaixo:\n\n"
                f"=== BANCO DE MEMÓRIA DO USUÁRIO ({nome_usuario.upper()}) ===\n"
                f"{resumo_fatos}\n"
                f"=============================================================\n"
            )
        }

        lista_mensagens = [instrucao_sistema]
        lista_mensagens.extend(obter_historico_recente_sql(usuario_id))
        lista_mensagens.append({"role": "user", "content": mensagem_usuario})

        try:
            resposta = ollama.chat(model=self.modelo, messages=lista_mensagens)
            return resposta['message']['content']
        except Exception as erro:
            print(f"\n❌ [ERRO OLLAMA]: {erro}")
            return "Ocorreu um erro ao comunicar com o modelo do Ollama."

    def _extrair_e_guardar_fatos(self, usuario_id: int, mensagem_usuario: str):
        texto_lc = mensagem_usuario.lower()
        gatilhos = [
            "torço", "meu time", "clube", "santos", "flamengo", "palmeiras", "corinthians",
            "gosto de", "meu nome", "moro em", "tenho", "favorito", "prefiro", "sou de", "trabalho",
            "jogo", "filme", "livro", "comida", "hobby", "interesse", "viagem", "cidade", "país","animal", "esporte", "música", "cantor",
            "banda", "programa de TV", "série", "personagem", "herói","personagem de filme", "personagem de série", "personagem de livro",
            "personagem de quadrinhos", "personagem de desenho animado","personagem de videogame", "personagem de anime", "personagem de mangá",
            "personagem de novela", "personagem de reality show","pokemons",
        ]

        if any(g in texto_lc for g in gatilhos):
            resumo_atual = obter_resumo_memoria(usuario_id)
            novo_fato = f"- {mensagem_usuario.strip()}"

            if novo_fato not in resumo_atual:
                if resumo_atual == "Nenhum fato registrado ainda.":
                    atualizar_resumo_memoria(usuario_id, novo_fato)
                else:
                    atualizar_resumo_memoria(usuario_id, f"{resumo_atual}\n{novo_fato}")


# =============================================================================
# MÓDULO 3: CAMADA DE INTEGRAÇÃO
# =============================================================================

_instancia_sky = None

def inicializar_sistema_sky():
    global _instancia_sky
    inicializar_banco_dados()
    _instancia_sky = AgenteSky()


def processar_mensagem_gui(usuario_id: int, nome_usuario: str, texto_usuario: str) -> str:
    global _instancia_sky
    if not _instancia_sky:
        inicializar_sistema_sky()

    if not texto_usuario.strip():
        return ""

    resposta = _instancia_sky.responder(usuario_id, nome_usuario, texto_usuario)
    salvar_conversa_sql(usuario_id, texto_usuario, resposta)
    return resposta


# =============================================================================
# EXECUÇÃO NO TERMINAL
# =============================================================================

if __name__ == "__main__":
    inicializar_sistema_sky()

    print("\n========================================================")
    print("  IA SKY - MODELO AVANÇADO LLAMA 3.1 (8B)                ")
    print("========================================================\n")

    usuario_id_ativo = None
    nome_ativo = ""

    while True:
        print("🔐 --- TELA DE AUTENTICAÇÃO ---")
        nome_input = input("👤 Nome de usuário: ")
        senha_input = input("🔑 Senha: ")

        sucesso, user_id, msg = autenticar_ou_cadastrar_usuario(nome_input, senha_input)
        print(f"\n{msg}\n")

        if sucesso:
            usuario_id_ativo = user_id
            nome_ativo = nome_input.strip().title()
            break

    print(f"✨ Chat iniciado com a SKY (Llama 3.1) para [{nome_ativo}]. Digite 'sair' para encerrar.\n")

    while True:
        entrada = input(f"📩 [{nome_ativo}]: ")

        if entrada.lower().strip() in ["sair", "exit", "quit"]:
            print("\n👋 [SKY]: Até breve!")
            break

        if entrada.strip():
            resposta = processar_mensagem_gui(usuario_id_ativo, nome_ativo, entrada)
            print(f"\n✨ [SKY]: {resposta}\n")