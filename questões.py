import streamlit as st
import json
import pandas as pd
import uuid
import random
from supabase import create_client, Client

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Meu App de Questões", layout="wide")

# --- CONEXÃO COM O SUPABASE ---
@st.cache_resource
def iniciar_conexao_supabase() -> Client:
    url = "https://jejoqyyksybgnqccnajf.supabase.co"
    key = "sb_publishable_UIKEbxQp6JXo26WiwVoSrg_gKfjhrnD"
    return create_client(url, key)

supabase = iniciar_conexao_supabase()

# --- FUNÇÕES DE BANCO DE DADOS COM CACHE ---
@st.cache_data(ttl=600)
def carregar_questoes():
    resposta = supabase.table("questoes").select("*").execute()
    return resposta.data

@st.cache_data(ttl=60)
def carregar_resultados(usuario):
    resposta = supabase.table("resultados").select("*").eq("usuario", usuario).execute()
    return resposta.data

def salvar_questoes(novas_questoes):
    supabase.table("questoes").insert(novas_questoes).execute()
    st.cache_data.clear() # Limpa apenas ao adicionar novas questões

def salvar_resultado(resultado):
    # Removido st.cache_data.clear() daqui para evitar que a questão suma da tela ao responder
    supabase.table("resultados").insert(resultado).execute()

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'usuario' not in st.session_state:
    st.session_state.usuario = ""

if not st.session_state.logado:
    st.title("📚 Sistema de Questões")
    st.info("Digite suas credenciais para acessar.")
    
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    
    usuarios_permitidos = {"Emerson": "1111", "Adrielle": "1234"}
    
    if st.button("Entrar"):
        if usuario in usuarios_permitidos and usuarios_permitidos[usuario] == senha:
            st.session_state.logado = True
            st.session_state.usuario = usuario
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
else:
    st.sidebar.title(f"Bem-vindo(a), {st.session_state.usuario}!")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    aba_resolver, aba_relatorios, aba_adicionar = st.tabs(["✍️ Resolver Questões", "📊 Relatórios", "➕ Adicionar Questões"])

    questoes = carregar_questoes()

    # --- ABA 1: RESOLVER QUESTÕES ---
    with aba_resolver:
        st.header("Resolver Questões")
        
        # O histórico é carregado no início da aba
        meus_resultados = carregar_resultados(st.session_state.usuario)
        questoes_feitas = set([r['id_questao'] for r in meus_resultados])
        questoes_erradas = set([r['id_questao'] for r in meus_resultados if not r['acertou']])
        
        if not questoes:
            st.warning("Nenhuma questão cadastrada ainda.")
        else:
            col1, col2, col3 = st.columns(3)
            filtro_historico = col1.selectbox("Histórico:", ["Todas", "Nunca feitas", "Já feitas", "Só as que errei", "Simulado (40 questões)"])
            
            if filtro_historico == "Simulado (40 questões)":
                if 'simulado_gerado' not in st.session_state or st.session_state.get('filtro_atual') != "Simulado (40 questões)":
                    q_inf = [q for q in questoes if q.get("bloco") == "Informática"]
                    q_cg = [q for q in questoes if q.get("bloco") == "Conhecimentos Gerais"]
                    q_ce = [q for q in questoes if q.get("bloco") == "Conhecimentos Específicos"]
                    
                    s_inf = random.sample(q_inf, min(10, len(q_inf)))
                    s_cg = random.sample(q_cg, min(10, len(q_cg)))
                    s_ce = random.sample(q_ce, min(20, len(q_ce)))
                    
                    simulado = s_inf + s_cg + s_ce
                    random.shuffle(simulado)
                    st.session_state.simulado_gerado = simulado
                
                questoes_filtradas = st.session_state.simulado_gerado
                st.session_state.filtro_atual = filtro_historico
                col2.info("Filtros fixos no Simulado.")
            else:
                st.session_state.filtro_atual = filtro_historico
                questoes_filtradas = questoes
                
                if filtro_historico == "Nunca feitas":
                    questoes_filtradas = [q for q in questoes_filtradas if q['id'] not in questoes_feitas]
                elif filtro_historico == "Já feitas":
                    questoes_filtradas = [q for q in questoes_filtradas if q['id'] in questoes_feitas]
                elif filtro_historico == "Só as que errei":
                    questoes_filtradas = [q for q in questoes_filtradas if q['id'] in questoes_erradas]

                blocos_disponiveis = sorted(list(set([q.get("bloco", "") for q in questoes_filtradas])))
                bloco_selecionado = col2.selectbox("Escolha o Bloco:", ["Todos"] + blocos_disponiveis)
                
                if bloco_selecionado != "Todos":
                    questoes_filtradas = [q for q in questoes_filtradas if q.get("bloco") == bloco_selecionado]
                
                temas_disponiveis = sorted(list(set([q.get("tema", "") for q in questoes_filtradas])))
                tema_selecionado = col3.selectbox("Escolha o Tema:", ["Todos"] + temas_disponiveis)
                
                if tema_selecionado != "Todos":
                    questoes_filtradas = [q for q in questoes_filtradas if q.get("tema") == tema_selecionado]

            itens_por_pagina = 10
            total_paginas = max(1, len(questoes_filtradas) // itens_por_pagina + (1 if len(questoes_filtradas) % itens_por_pagina > 0 else 0))
            
            if len(questoes_filtradas) > itens_por_pagina:
                pag_col1, pag_col2 = st.columns([1, 4])
                pagina_atual = pag_col1.number_input("Página", min_value=1, max_value=total_paginas, step=1)
            else:
                pagina_atual = 1

            inicio = (pagina_atual - 1) * itens_por_pagina
            fim = inicio + itens_por_pagina
            lote_questoes = questoes_filtradas[inicio:fim]

            st.write(f"Exibindo {len(lote_questoes)} de {len(questoes_filtradas)} questões (Página {pagina_atual}/{total_paginas})")
            st.divider()

            for i, q in enumerate(lote_questoes):
                indice_real = inicio + i + 1
                st.markdown(f"**Q{indice_real}. ({q['bloco']})** {q['enunciado']}")
                
                resposta_usuario = st.radio("Alternativas:", q['opcoes'], key=f"radio_{q['id']}", index=None)
                
                if st.button("Responder", key=f"btn_{q['id']}"):
                    if resposta_usuario:
                        acertou = (resposta_usuario == q['resposta_correta'])
                        salvar_resultado({
                            "usuario": st.session_state.usuario,
                            "id_questao": q['id'],
                            "bloco": q['bloco'],
                            "tema": q['tema'],
                            "acertou": acertou
                        })
                        
                        if acertou:
                            msg = random.choice(["Acertou! nunca duvidei ein", "A minzeravi, quem te ensinou? Acertou!","também né, essa até minha vó acertaria","Foi cagada, aposto, mas acertou!"]) if st.session_state.usuario == "Adrielle" else "✅ Resposta Correta!"
                            st.success(msg)
                        else:
                            msg = random.choice(["errou feio, errou rude.", "errou, véia pôde.","Tinha que ser baiana.. Errou!","Tá dificil é? Não acerta uma"]) if st.session_state.usuario == "Adrielle" else "❌ Resposta Incorreta."
                            st.error(f"{msg} A correta era: {q['resposta_correta']}")
                        
                        with st.expander("Ver Explicação", expanded=True):
                            st.write(q['explicacao'])
                    else:
                        st.warning("Selecione uma alternativa.")
                st.divider()

    # --- ABA 2: RELATÓRIOS ---
    with aba_relatorios:
        st.header("Seu Desempenho")
        # Forçamos a limpeza do cache aqui para que o relatório mostre os dados que acabaram de ser respondidos
        st.cache_data.clear() 
        meus_resultados = carregar_resultados(st.session_state.usuario)
        
        if not meus_resultados:
            st.info("Nenhuma questão respondida.")
        else:
            df = pd.DataFrame(meus_resultados)
            c1, c2, c3 = st.columns(3)
            c1.metric("Respondidas", len(df))
            c2.metric("Acertos", int(df['acertou'].sum()))
            c3.metric("Taxa", f"{(df['acertou'].sum()/len(df))*100:.1f}%")
            st.bar_chart(df.groupby('bloco')['acertou'].mean() * 100)

    # --- ABA 3: ADICIONAR QUESTÕES ---
    with aba_adicionar:
        st.header("Adicionar Questões")
        
        # 1. Listas fixas que você quer que sempre apareçam (nunca somem)
        blocos_fixos = ["Conhecimentos Específicos", "Conhecimentos Gerais", "Informática"]
        temas_fixos = ["Administração Pública...", "Gestão de documentos...", "Redação oficial..."]

        # 2. Puxa os blocos e temas que já existem no banco
        blocos_banco = [q.get("bloco", "") for q in questoes if q.get("bloco")]
        temas_banco = [q.get("tema", "") for q in questoes if q.get("tema")]
        
        # 3. Junta as listas fixas com as do banco e remove duplicadas
        blocos_existentes = sorted(list(set(blocos_fixos + blocos_banco)))
        temas_existentes = sorted(list(set(temas_fixos + temas_banco)))
        
        c1, c2 = st.columns(2)
        
        # 4. Lógica para o BLOCO (Selecionar da lista combinada ou criar novo)
        opcao_bloco = c1.selectbox("Bloco:", blocos_existentes + ["➕ Criar Novo Bloco..."])
        if opcao_bloco == "➕ Criar Novo Bloco...":
            novo_bloco = c1.text_input("Digite o nome do novo Bloco:")
        else:
            novo_bloco = opcao_bloco

        # 5. Lógica para o TEMA (Selecionar da lista combinada ou criar novo)
        opcao_tema = c2.selectbox("Tema:", temas_existentes + ["➕ Criar Novo Tema..."])
        if opcao_tema == "➕ Criar Novo Tema...":
            novo_tema = c2.text_input("Digite o nome do novo Tema:")
        else:
            novo_tema = opcao_tema
        
        json_input = st.text_area("Cole o JSON aqui:", height=200)
        
        if st.button("Importar"):
            if not novo_bloco or not novo_tema:
                st.warning("Por favor, selecione ou digite um Bloco e um Tema válidos.")
            elif not json_input.strip():
                st.warning("O campo do JSON está vazio.")
            else:
                try:
                    novas = json.loads(json_input)
                    for nq in novas:
                        nq['id'] = str(uuid.uuid4())
                        nq['bloco'] = novo_bloco.strip()
                        nq['tema'] = novo_tema.strip()
                    salvar_questoes(novas)
                    st.success("✅ Importado com sucesso!")
                except json.JSONDecodeError:
                    st.error("Erro no formato JSON. Verifique se copiou corretamente.")
                except Exception as e:
                    st.error(f"Erro: {e}")