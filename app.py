# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import io
import time
import re

# Importa a lógica blindada do seu arquivo automacao_sigaa.py
from automacao_sigaa import executar_automacao, BIBLIOTECA_MAP

# =====================================================================================
# CONFIGURAÇÃO GERAL DA PÁGINA
# =====================================================================================

st.set_page_config(
    page_title="Relatório Automatizado UFPB", 
    page_icon="📚", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================================
# ESTILIZAÇÃO CSS (Paleta Biblioteca Central: Cinza Predominante + Azul)
# =====================================================================================
st.markdown(
    """
    <style>
    /* 1. Esconde elementos nativos do Streamlit */
    .stDeployButton {display:none;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    
    /* 2. Esconde 'Press Enter to submit' */
    [data-testid="InputInstructions"] { display: none !important; }
    
    /* --- PALETA DE CORES BIBLIOTECA CENTRAL --- */
    
    /* Fundo Geral (Cinza Claro Institucional) */
    .stApp { 
        background-color: #F4F4F4; 
    }
    
    /* Sidebar (Branco ou Cinza muito leve para contraste) */
    [data-testid="stSidebar"] {
        background-color: #EAEAEA;
        border-right: 1px solid #D1D1D1;
    }
    
    /* Cabeçalhos e Textos (Cinza Escuro Chumbo) */
    h1, h2, h3, .stMarkdown {
        color: #333333 !important;
    }
    
    /* Botão Principal (Azul Institucional - Sóbrio) */
    .stButton>button { 
        background-color: #2C5282; /* Azul Biblioteca */
        color: white; 
        border-radius: 6px; 
        font-weight: 600;
        border: none;
        padding: 0.6rem 1rem;
        width: 100%;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover { 
        background-color: #1A365D; /* Azul mais escuro ao passar o mouse */
        color: #F0F0F0; 
    }

    /* Inputs (Caixas de Texto) */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        background-color: #FFFFFF;
        border: 1px solid #CCCCCC;
        color: #333333;
    }
    .stTextInput>div>div>input:focus, .stSelectbox>div>div>div:focus {
        border-color: #2C5282; /* Borda azul ao digitar */
    }

    /* Caixa de Informação Personalizada (Estilo Cinza com detalhe Azul) */
    .info-box {
        background-color: #E0E0E0; /* Cinza médio */
        padding: 15px; 
        border-radius: 8px; 
        border-left: 6px solid #2C5282; /* Detalhe azul */
        color: #333333;
        margin-bottom: 20px;
        font-size: 0.95rem;
    }
    
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================================================================================
# BARRA LATERAL (Navegação)
# =====================================================================================
with st.sidebar:
    st.header("Relatório Automatizado")
    st.markdown("**Sistema Integrado UFPB**")
    st.markdown("---")
    nav = st.radio("Menu", ["Pesquisa", "Como Funciona"])
    st.markdown("---")
    st.caption("Versão 1.0 (Stable)")

# =====================================================================================
# CLASSE DE LOGS (Para comunicação entre o Robô e o Site)
# =====================================================================================
class StatusProxy:
    def __init__(self):
        self.placeholder = st.empty()
        self.log_history = []
    
    def put(self, msg):
        self.log_history.append(f"🔹 {msg}")
        self.placeholder.code("\n".join(self.log_history[-3:]))
    
    def update(self, label, state):
        if state == 'error': st.error(label)
        elif state == 'complete': st.success(label)
        else: self.put(label)

# =====================================================================================
# TELA 1: PESQUISA (Layout Ajustado)
# =====================================================================================
if nav == "Pesquisa":
    st.title("Relatório Automatizado UFPB")
    
    # Caixa de aviso estilizada (Cinza + Azul)
    st.markdown("""
    <div class="info-box">
        O sistema buscará os livros, verificará volumes e filtrará automaticamente as informações irrelevantes (Localização, Status, etc).
        <br><b>O arquivo final conterá apenas os dados prontos para uso.</b>
    </div>
    """, unsafe_allow_html=True)

    with st.form("form_principal"):
        # LINHA SUPERIOR: Título e Autor
        c_sup_1, c_sup_2 = st.columns([1, 1])
        with c_sup_1:
            titulo = st.text_input("Título do Livro", placeholder="Ex: Princípios de Química")
        with c_sup_2:
            autor = st.text_input("Autor", placeholder="Ex: Atkins")
        
        # LINHA INFERIOR: Volume e Biblioteca
        c_inf_1, c_inf_2 = st.columns([1, 1])
        with c_inf_1:
            volume = st.text_input("Volume", placeholder="Digite apenas o número (Ex: 1)")
        with c_inf_2:
            bib_options = ["TODAS AS BIBLIOTECAS"] + list(BIBLIOTECA_MAP.keys())
            biblioteca = st.selectbox("Biblioteca", bib_options)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Botão Centralizado
        col_btn_1, col_btn_2, col_btn_3 = st.columns([1, 1, 1])
        with col_btn_2:
            btn_iniciar = st.form_submit_button("Gerar Relatório")

    if btn_iniciar:
        if not titulo:
            st.warning("⚠️ Por favor, digite o Título do livro.")
        else:
            status_box = StatusProxy()
            
            with st.spinner("⏳ Processando acervo..."):
                excel_bytes, nome_arq = executar_automacao(titulo, autor, volume, biblioteca, status_box)
            
            if excel_bytes:
                st.balloons()
                st.success("✅ Relatório gerado com sucesso!")
                
                c_dl_1, c_dl_2, c_dl_3 = st.columns([1, 2, 1])
                with c_dl_2:
                    st.download_button(
                        label="📥 BAIXAR EXCEL AGORA",
                        data=excel_bytes,
                        file_name=nome_arq,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
            else:
                st.warning("🔍 Nenhum livro encontrado com esses critérios ou falha na conexão.")

# =====================================================================================
# TELA 2: COMO FUNCIONA
# =====================================================================================
elif nav == "Como Funciona":
    st.title("📖 Guia de Uso")
    
    st.markdown("### Passo a Passo")
    
    st.markdown("""
    1. **Digite o título do livro** no campo principal.
    2. **Digite o autor do livro** (opcional, para refinar a busca).
    3. **Digite o volume do livro** (caso deixe em branco, serão coletados todos os volumes).
    4. **Clique em "Gerar Relatório"**.
    """)
    
    st.info("💡 O sistema gera um arquivo Excel organizado por Biblioteca e Coleção.")