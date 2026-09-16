"""
===============================================================================
PROJETO FINAL: IA "SKY" com Tkinter, Temas (Claro/Escuro), JSON e Ollama Otimizado
===============================================================================
"""

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

try:
    import ollama
except ImportError:
    messagebox.showerror("Erro de Importação", "A biblioteca 'ollama' não está instalada.\nExecute: pip install ollama")
    sys.exit(1)


MODELO_AVANCADO_OLLAMA = "llama3.1:8b"
NOME_BANCO_DADOS = "historico_sky.db"
ARQUIVO_CONFIG_JSON = "config.json"
LIMITE_MENSAGENS_RECENTES = 6  # Reduzido para acelerar o contexto enviado à IA


# =============================================================================
# MÓDULO DE CONFIGURAÇÃO JSON
# =============================================================================

CONFIG_PADRAO = {
    "tema": "escuro",
    "modelo": MODELO_AVANCADO_OLLAMA,
    "limite_historico": LIMITE_MENSAGENS_RECENTES
}

def carregar_configuracao() -> dict:
    """Carrega as configurações do arquivo JSON ou cria um padrão."""
    if not os.path.exists(ARQUIVO_CONFIG_JSON):
        salvar_configuracao(CONFIG_PADRAO)
        return CONFIG_PADRAO.copy()
    try:
        with open(ARQUIVO_CONFIG_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return CONFIG_PADRAO.copy()

def salvar_configuracao(config: dict):
    """Grava as configurações atualizadas no arquivo JSON."""
    try:
        with open(ARQUIVO_CONFIG_JSON, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar JSON: {e}")


# =============================================================================
# MÓDULO 1: BANCO DE DADOS SQLITE
# =============================================================================

def encriptar_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def inicializar_banco_dados():
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


def autenticar_ou_cadastrar_usuario(nome_usuario: str, senha_digitada: str) -> tuple:
    nome_limpo = nome_usuario.strip().title()
    senha_hash = encriptar_senha(senha_digitada.strip())

    if not nome_limpo or not senha_digitada.strip():
        return False, None, "Preencha o nome de usuário e a senha."

    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    cursor = conexao.cursor()

    cursor.execute("SELECT id, senha_hash FROM usuarios WHERE nome = ?;", (nome_limpo,))
    usuario = cursor.fetchone()

    if usuario:
        usuario_id, hash_salvo = usuario
        if hash_salvo == senha_hash:
            conexao.close()
            return True, usuario_id, f"Bem-vindo(a) de volta, {nome_limpo}!"
        conexao.close()
        return False, None, "Senha incorreta! Acesso negado."

    cursor.execute("INSERT INTO usuarios (nome, senha_hash) VALUES (?, ?);", (nome_limpo, senha_hash))
    usuario_id = cursor.lastrowid
    cursor.execute("INSERT INTO memoria_resumida (usuario_id, resumo) VALUES (?, ?);", (usuario_id, "Nenhum fato registrado ainda."))
    conexao.commit()
    conexao.close()
    return True, usuario_id, f"Novo usuário '{nome_limpo}' cadastrado com sucesso!"


def salvar_conversa_sql(usuario_id: int, usuario_msg: str, resposta_sky: str):
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
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    cursor = conexao.cursor()
    cursor.execute("SELECT resumo FROM memoria_resumida WHERE usuario_id = ?;", (usuario_id,))
    resultado = cursor.fetchone()
    conexao.close()
    return resultado[0] if resultado else "Nenhum fato registrado ainda."


def atualizar_resumo_memoria(usuario_id: int, novo_resumo: str):
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    cursor = conexao.cursor()
    cursor.execute("UPDATE memoria_resumida SET resumo = ? WHERE usuario_id = ?;", (novo_resumo, usuario_id))
    conexao.commit()
    conexao.close()


def obter_historico_recente_sql(usuario_id: int, limite: int = LIMITE_MENSAGENS_RECENTES) -> list:
    conexao = sqlite3.connect(NOME_BANCO_DADOS)
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT usuario_msg, resposta_sky FROM conversas 
        WHERE usuario_id = ?
        ORDER BY id DESC LIMIT ?;
    """, (usuario_id, limite))

    registros = cursor.fetchall()
    conexao.close()
    registros.reverse()

    historico_formatado = []
    for msg_user, msg_sky in registros:
        if msg_user.strip():
            historico_formatado.append({"role": "user", "content": msg_user})
        if msg_sky.strip():
            historico_formatado.append({"role": "assistant", "content": msg_sky})

    return historico_formatado


# =============================================================================
# MÓDULO 2: CLASSE DA IA "SKY" (OTIMIZADA)
# =============================================================================

class AgenteSky:
    def __init__(self, modelo: str = MODELO_AVANCADO_OLLAMA):
        self.modelo = modelo

    def _obter_contexto_temporal(self) -> str:
        agora = datetime.now()
        dias_semana = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
        return f"{dias_semana[agora.weekday()]}, {agora.strftime('%d/%m/%Y às %H:%M:%S')}"

    def _extrair_e_guardar_fatos(self, usuario_id: int, mensagem_usuario: str):
        texto_lc = mensagem_usuario.lower()
        gatilhos = ["torço", "meu time", "clube", "santos", "flamengo", "palmeiras", "corinthians", "gosto de", "meu nome", "moro em", "tenho", "favorito", "prefiro", "sou de", "trabalho", "jogo", "filme", "livro", "comida", "hobby"]

        if any(g in texto_lc for g in gatilhos):
            resumo_atual = obter_resumo_memoria(usuario_id)
            novo_fato = f"- {mensagem_usuario.strip()}"

            if novo_fato not in resumo_atual:
                if resumo_atual == "Nenhum fato registrado ainda.":
                    atualizar_resumo_memoria(usuario_id, novo_fato)
                else:
                    atualizar_resumo_memoria(usuario_id, f"{resumo_atual}\n{novo_fato}")

    def responder(self, usuario_id: int, nome_usuario: str, mensagem_usuario: str) -> str:
        self._extrair_e_guardar_fatos(usuario_id, mensagem_usuario)
        momento_atual = self._obter_contexto_temporal()
        resumo_fatos = obter_resumo_memoria(usuario_id)

        instrucao_sistema = {
            "role": "system",
            "content": (
                f"Você é a SKY, assistente virtual direta, objetiva e precisa.\n"
                f"Conversando com: {nome_usuario} | Data/Hora: {momento_atual}\n"
                f"MEMÓRIA DE {nome_usuario.upper()}:\n{resumo_fatos}\n"
                f"Responda de forma ágil e sem enrolação."
            ),
        }

        lista_mensagens = [instrucao_sistema]
        lista_mensagens.extend(obter_historico_recente_sql(usuario_id))
        lista_mensagens.append({"role": "user", "content": mensagem_usuario})

        try:
            # Otimização via parâmetros do Ollama para respostas mais rápidas
            resposta = ollama.chat(
                model=self.modelo,
                messages=lista_mensagens,
                options={
                    "num_predict": 300,
                    "temperature": 0.6,
                    "top_k": 20,
                    "top_p": 0.85
                }
            )
            return resposta["message"]["content"]
        except Exception as erro:
            return f"❌ Erro de conexão com Ollama: {erro}"


# =============================================================================
# MÓDULO 3: INTERFACE GRÁFICA TKINTER COM SUAS CORES EXATAS
# =============================================================================

# Dicionário de temas mantendo EXATAMENTE a sua paleta no modo escuro
PALETAS = {
    "escuro": {
        "COR_FUNDO_JANELA": "#1e1e2e",
        "COR_FUNDO_TOPO": "#181825",
        "COR_CAMPO_TEXTO": "#313244",
        "COR_TEXTO_PADRAO": "#cdd6f4",
        "COR_TEXTO_SUBTITULO": "#a6adc8",
        "COR_TITULO": "#ecb743",
        "COR_BOTAO_LOGIN": "#89b4fa",
        "COR_BOTAO_MEMORIA": "#fbff00",
        "COR_BOTAO_TEMA": "#89b4fa",
        "COR_BOTAO_ENVIAR": "#fff4f4",
        "COR_TEXTO_BOTAO": "#11111b",
        "COR_NOME_USUARIO": "#e2e2e2",
        "COR_NOME_SKY": "#00bcdd",
    },
    "claro": {
        "COR_FUNDO_JANELA": "#f4f4f9",
        "COR_FUNDO_TOPO": "#e2e2e9",
        "COR_CAMPO_TEXTO": "#ffffff",
        "COR_TEXTO_PADRAO": "#11111b",
        "COR_TEXTO_SUBTITULO": "#555566",
        "COR_TITULO": "#b57c00",
        "COR_BOTAO_LOGIN": "#2b6cb0",
        "COR_BOTAO_MEMORIA": "#d69e2e",
        "COR_BOTAO_TEMA": "#4a5568",
        "COR_BOTAO_ENVIAR": "#2b6cb0",
        "COR_TEXTO_BOTAO": "#ffffff",
        "COR_NOME_USUARIO": "#2d3748",
        "COR_NOME_SKY": "#00838f",
    }
}


class AppSky:
    def __init__(self, root):
        self.root = root
        self.root.title("IA SKY - Assistente Pessoal")
        self.root.geometry("600x700")

        # Carrega preferências do JSON
        self.config = carregar_configuracao()
        self.modo_tema = self.config.get("tema", "escuro")
        self.carregar_paleta()

        self.agente = AgenteSky(self.config.get("modelo", MODELO_AVANCADO_OLLAMA))
        self.usuario_id = None
        self.nome_usuario = ""

        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.criar_tela_login()

    def carregar_paleta(self):
        """Atribui as cores atuais com base no modo selecionado."""
        p = PALETAS[self.modo_tema]
        self.COR_FUNDO_JANELA    = p["COR_FUNDO_JANELA"]
        self.COR_FUNDO_TOPO      = p["COR_FUNDO_TOPO"]
        self.COR_CAMPO_TEXTO     = p["COR_CAMPO_TEXTO"]
        self.COR_TEXTO_PADRAO    = p["COR_TEXTO_PADRAO"]
        self.COR_TEXTO_SUBTITULO = p["COR_TEXTO_SUBTITULO"]
        self.COR_TITULO          = p["COR_TITULO"]
        self.COR_BOTAO_LOGIN     = p["COR_BOTAO_LOGIN"]
        self.COR_BOTAO_MEMORIA   = p["COR_BOTAO_MEMORIA"]
        self.COR_BOTAO_TEMA      = p["COR_BOTAO_TEMA"]
        self.COR_BOTAO_ENVIAR    = p["COR_BOTAO_ENVIAR"]
        self.COR_TEXTO_BOTAO     = p["COR_TEXTO_BOTAO"]
        self.COR_NOME_USUARIO    = p["COR_NOME_USUARIO"]
        self.COR_NOME_SKY        = p["COR_NOME_SKY"]

        self.root.configure(bg=self.COR_FUNDO_JANELA)

    def alternar_tema(self):
        """Alterna entre o modo escuro e claro em tempo real e atualiza o JSON."""
        self.modo_tema = "claro" if self.modo_tema == "escuro" else "escuro"
        self.config["tema"] = self.modo_tema
        salvar_configuracao(self.config)
        
        self.carregar_paleta()

        # Recria a tela ativa para aplicar as novas cores
        if hasattr(self, "frame_login") and self.frame_login.winfo_exists():
            self.frame_login.destroy()
            self.criar_tela_login()
        elif hasattr(self, "area_chat"):
            for widget in self.root.winfo_children():
                widget.destroy()
            self.criar_tela_chat()

    def criar_tela_login(self):
        """Monta o painel de Login/Cadastro."""
        self.frame_login = tk.Frame(self.root, bg=self.COR_FUNDO_JANELA)
        self.frame_login.pack(expand=True)

        # Botão para alternar tema na tela de login
        btn_tema = tk.Button(
            self.frame_login,
            text=f"Modo {'Claro' if self.modo_tema == 'escuro' else 'Escuro'}",
            font=("Helvetica", 9, "bold"),
            bg=self.COR_BOTAO_TEMA,
            fg=self.COR_TEXTO_BOTAO,
            relief="flat",
            command=self.alternar_tema,
            cursor="hand2"
        )
        btn_tema.pack(anchor="ne", pady=(0, 10))

        tk.Label(self.frame_login, text="✨ IA SKY", font=("Helvetica", 24, "bold"), fg=self.COR_TITULO, bg=self.COR_FUNDO_JANELA).pack(pady=20)
        tk.Label(self.frame_login, text="Autenticação do Usuário", font=("Helvetica", 12), fg=self.COR_TEXTO_SUBTITULO, bg=self.COR_FUNDO_JANELA).pack(pady=5)

        tk.Label(self.frame_login, text="Usuário:", fg=self.COR_TEXTO_PADRAO, bg=self.COR_FUNDO_JANELA, font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(10, 2))
        self.ent_usuario = tk.Entry(self.frame_login, font=("Helvetica", 12), width=30, bg=self.COR_CAMPO_TEXTO, fg=self.COR_TEXTO_PADRAO, insertbackground=self.COR_TEXTO_PADRAO, relief="flat")
        self.ent_usuario.pack(pady=5, ipady=5)

        tk.Label(self.frame_login, text="Senha:", fg=self.COR_TEXTO_PADRAO, bg=self.COR_FUNDO_JANELA, font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(10, 2))
        self.ent_senha = tk.Entry(self.frame_login, show="*", font=("Helvetica", 12), width=30, bg=self.COR_CAMPO_TEXTO, fg=self.COR_TEXTO_PADRAO, insertbackground=self.COR_TEXTO_PADRAO, relief="flat")
        self.ent_senha.pack(pady=5, ipady=5)

        btn_entrar = tk.Button(self.frame_login, text="Entrar / Cadastrar", font=("Helvetica", 11, "bold"), bg=self.COR_BOTAO_LOGIN, fg=self.COR_TEXTO_BOTAO, relief="flat", command=self.acao_login, cursor="hand2")
        btn_entrar.pack(pady=20, fill="x", ipady=5)

    def acao_login(self):
        nome = self.ent_usuario.get()
        senha = self.ent_senha.get()

        sucesso, user_id, msg = autenticar_ou_cadastrar_usuario(nome, senha)

        if sucesso:
            self.usuario_id = user_id
            self.nome_usuario = nome.strip().title()
            messagebox.showinfo("Sucesso", msg)
            self.frame_login.destroy()
            self.criar_tela_chat()
        else:
            messagebox.showerror("Acesso Negado", msg)

    def criar_tela_chat(self):
        """Monta o Chat principal."""
        frame_topo = tk.Frame(self.root, bg=self.COR_FUNDO_TOPO, height=50)
        frame_topo.pack(fill="x")

        lbl_titulo = tk.Label(frame_topo, text=f"✨ Conversando com SKY [{self.nome_usuario}]", font=("Helvetica", 12, "bold"), fg=self.COR_TITULO, bg=self.COR_FUNDO_TOPO)
        lbl_titulo.pack(side="left", padx=15, pady=10)

        # Botão Tema no topo
        btn_tema = tk.Button(frame_topo, text="🎨 Tema", bg=self.COR_BOTAO_TEMA, fg=self.COR_TEXTO_BOTAO, font=("Helvetica", 9, "bold"), relief="flat", command=self.alternar_tema, cursor="hand2")
        btn_tema.pack(side="right", padx=(5, 15))

        # Botão Memória no topo
        btn_memoria = tk.Button(frame_topo, text="🧠 Memória", bg=self.COR_BOTAO_MEMORIA, fg=self.COR_TEXTO_BOTAO, font=("Helvetica", 9, "bold"), relief="flat", command=self.exibir_memoria_box, cursor="hand2")
        btn_memoria.pack(side="right", padx=5)

        self.area_chat = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, font=("Helvetica", 11), bg=self.COR_FUNDO_JANELA, fg=self.COR_TEXTO_PADRAO, relief="flat")
        self.area_chat.pack(padx=15, pady=10, fill="both", expand=True)
        self.area_chat.config(state="disabled")

        self.area_chat.tag_config("user", foreground=self.COR_NOME_USUARIO, font=("Helvetica", 11, "bold"))
        self.area_chat.tag_config("sky", foreground=self.COR_NOME_SKY, font=("Helvetica", 11))

        frame_input = tk.Frame(self.root, bg=self.COR_FUNDO_JANELA)
        frame_input.pack(fill="x", padx=15, pady=(0, 15))

        self.ent_msg = tk.Entry(frame_input, font=("Helvetica", 11), bg=self.COR_CAMPO_TEXTO, fg=self.COR_TEXTO_PADRAO, insertbackground=self.COR_TEXTO_PADRAO, relief="flat")
        self.ent_msg.pack(side="left", fill="both", expand=True, ipady=8, padx=(0, 10))
        self.ent_msg.bind("<Return>", lambda event: self.enviar_mensagem())

        btn_enviar = tk.Button(frame_input, text="Enviar 🚀", font=("Helvetica", 10, "bold"), bg=self.COR_BOTAO_ENVIAR, fg=self.COR_TEXTO_BOTAO, relief="flat", command=self.enviar_mensagem, cursor="hand2")
        btn_enviar.pack(side="right", ipady=6, ipadx=10)

    def enviar_mensagem(self):
        texto = self.ent_msg.get().strip()
        if not texto:
            return

        self.ent_msg.delete(0, tk.END)
        self.adicionar_texto_chat(f"👤 {self.nome_usuario}: ", "user")
        self.adicionar_texto_chat(f"{texto}\n\n", "normal")

        # Processar resposta da SKY otimizada
        resposta = self.agente.responder(self.usuario_id, self.nome_usuario, texto)
        salvar_conversa_sql(self.usuario_id, texto, resposta)

        self.adicionar_texto_chat("✨ SKY: ", "sky")
        self.adicionar_texto_chat(f"{resposta}\n\n", "normal")

    def adicionar_texto_chat(self, texto: str, tag: str):
        self.area_chat.config(state="normal")
        self.area_chat.insert(tk.END, texto, tag)
        self.area_chat.config(state="disabled")
        self.area_chat.yview(tk.END)

    def exibir_memoria_box(self):
        fatos = obter_resumo_memoria(self.usuario_id)
        messagebox.showinfo(f"Memória Viva de {self.nome_usuario}", fatos)


# =============================================================================
# INICIALIZAÇÃO
# =============================================================================

if __name__ == "__main__":
    inicializar_banco_dados()
    root = tk.Tk()
    app = AppSky(root)
    root.mainloop()