import os
import urllib.request
import json
from io import BytesIO
import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader
from gtts import gTTS
from openai import OpenAI

# ==========================================
# BLOCO A: Importações e Configuração (OpenRouter)
# ==========================================
load_dotenv(override=True)
client = OpenAI(
    base_url="https://openrouter.ai",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# ==========================================
# BLOCO B: Leitura Otimizada do PDF (Em Cache)
# ==========================================
@st.cache_data
def extrair_texto_pdf(caminho_pdf):
    leitor = PdfReader(caminho_pdf)
    texto_completo = ""
    for pagina in leitor.pages:
        texto_completo += pagina.extract_text() + "\n"
    return " ".join(texto_completo.split())[:6000]

conteudo_folder = extrair_texto_pdf("Inteligencia_Artificial_para_Todos.pdf")

# ==========================================
# BLOCO C: Função de Áudio Sob Demanda
# ==========================================
@st.cache_data(show_spinner=False)
def gerar_audio(texto):
    texto_limpo = texto.replace("*", "").replace("#", "").replace(">", "")
    tts = gTTS(text=texto_limpo, lang="pt", slow=False)
    audio_bytes = BytesIO()
    tts.write_to_fp(audio_bytes)
    audio_bytes.seek(0)
    return audio_bytes.getvalue()

# ==========================================
# BLOCO D: Descoberta Automática de Modelos Gratuitos
# ==========================================
@st.cache_data(ttl=1800, show_spinner=False)
def obter_modelos_gratuitos():
    try:
        req = urllib.request.urlopen("https://openrouter.ai/models", timeout=5)
        dados = json.loads(req.read().decode("utf-8"))
        livres = [
            m["id"] for m in dados.get("data", [])
            if m.get("id", "").endswith(":free")
            and "vision" not in m.get("id", "").lower()
            and "image" not in m.get("id", "").lower()
        ]
        if livres:
            return ["openrouter/free"] + livres[:8]
    except Exception:
        pass
    return ["openrouter/free"]

# ==========================================
# BLOCO E: Consulta Rápida à IA com Fallback
# ==========================================
@st.cache_data(show_spinner=False)
def consultar_ia(pergunta, instrucoes):
    modelos = obter_modelos_gratuitos()
    ultimo_erro = None

    for modelo_atual in modelos:
        try:
            resposta = client.chat.completions.create(
                model=modelo_atual,
                messages=[
                    {"role": "system", "content": instrucoes},
                    {"role": "user", "content": pergunta}
                ],
                temperature=0.3,
                max_tokens=800
            )
            conteudo = resposta.choices[0].message.content
            if conteudo:
                return conteudo
        except Exception as e:
            ultimo_erro = e

    raise ultimo_erro

# ==========================================
# BLOCO F: Interface Web e Acessibilidade
# ==========================================
st.set_page_config(page_title="Assistente - IA para Todos", page_icon="🤖", layout="wide")
st.title("🤖 Assistente Virtual: Inteligência Artificial para Todos")
st.write("Tire suas dúvidas sobre o guia digital, crie prompts prontos e aprenda a usar a IA com segurança.")

instrucoes_sistema = f"""
Você é um assistente educativo do projeto 'Inteligência Artificial para Todos'.
Responda de forma clara, objetiva, rápida e acolhedora com base EXCLUSIVAMENTE no guia abaixo:

{conteudo_folder}

Regras obrigatórias:
1. Responda sempre em português do Brasil claro e didático.
2. Entenda qualquer pergunta feita pelo usuário (mesmo informal ou curta) e conecte-a aos temas do guia.
3. Para pedidos de anúncio, texto ou comando, entregue um exemplo completo usando a Fórmula do Comando Perfeito (Papel, Tarefa, Contexto) e lembre dos cuidados de privacidade.
4. Se perguntarem algo totalmente fora do tema do folder, explique gentilmente que seu foco é ajudar com o guia de IA.
"""

if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

st.markdown("**💡 Clique em um tema rápido ou escreva abaixo:**")
col1, col2, col3 = st.columns(3)
pergunta_sugerida = None

with col1:
    if st.button("🔒 Usar IA com segurança", use_container_width=True):
        pergunta_sugerida = "Quais são as 3 regras de ouro de segurança do guia?"
with col2:
    if st.button("📣 Criar anúncio no WhatsApp", use_container_width=True):
        pergunta_sugerida = "Me dê um exemplo completo de comando pronto para vender um produto no WhatsApp."
with col3:
    if st.button("📚 Usar IA nos estudos", use_container_width=True):
        pergunta_sugerida = "Como usar a IA para estudar melhor segundo o guia?"

st.markdown("---")

for idx, msg in enumerate(st.session_state.mensagens):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            if st.button("🔊 Ouvir resposta", key=f"btn_audio_{idx}"):
                with st.spinner("Preparando voz..."):
                    audio_dados = gerar_audio(msg["content"])
                    st.audio(audio_dados, format="audio/mp3", autoplay=True)

pergunta_digitada = st.chat_input("Digite sua dúvida aqui...")
pergunta_final = pergunta_sugerida or pergunta_digitada

if pergunta_final:
    st.session_state.mensagens.append({"role": "user", "content": pergunta_final})
    with st.chat_message("user"):
        st.markdown(pergunta_final)

    with st.chat_message("assistant"):
        with st.spinner("Consultando o guia..."):
            try:
                texto_resposta = consultar_ia(pergunta_final, instrucoes_sistema)
                st.markdown(texto_resposta)
                st.session_state.mensagens.append({"role": "assistant", "content": texto_resposta})
                idx_atual = len(st.session_state.mensagens) - 1
                if st.button("🔊 Ouvir resposta", key=f"btn_audio_{idx_atual}"):
                    with st.spinner("Preparando voz..."):
                        audio_dados = gerar_audio(texto_resposta)
                        st.audio(audio_dados, format="audio/mp3", autoplay=True)
            except Exception:
                aviso = "⏳ O servidor gratuito está com alto volume de acessos no momento. Aguarde alguns segundos e clique novamente!"
                st.warning(aviso)
                st.session_state.mensagens.append({"role": "assistant", "content": aviso})

with st.sidebar:
    st.header("♿ Acessibilidade")
    st.info("🔊 Clique em **'🔊 Ouvir resposta'** abaixo do texto para escutar em voz alta.")
    st.markdown("---")
    st.markdown("### 🤟 Tradução em Libras (VLibras)")
    st.write("Use a extensão gratuita **VLibras** no navegador ou copie o texto abaixo:")
    st.link_button("Abrir VLibras Oficial (Gov.br)", "https://www.gov.br")
    
    ultima_resposta = ""
    for msg in reversed(st.session_state.mensagens):
        if msg["role"] == "assistant":
            ultima_resposta = msg["content"]
            break
    if ultima_resposta:
        st.text_area("Última resposta (copiar):", value=ultima_resposta, height=150)
