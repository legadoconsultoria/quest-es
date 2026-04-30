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
    # URL corrigida (sem o /rest/v1/ no final)
    url = "https://jejoqyyksybgnqccnajf.supabase.co"
    key = "sb_publishable_UIKEbxQp6JXo26WiwVoSrg_gKfjhrnD"
    
    return create_client(url, key)

supabase = iniciar_conexao_supabase()

# --- FUNÇÕES DE BANCO DE DADOS (SUPABASE) ---
def carregar_questoes():
    resposta = supabase.table("questoes").select("*").execute()
    return resposta.data

def salvar_questoes(novas_questoes):
    # Inserir no Supabase (pode ser uma lista de dicionários)
    supabase.table("questoes").insert(novas_questoes).execute()

def carregar_resultados():
    resposta = supabase.table("resultados").select("*").execute()
    return resposta.data

def salvar_resultado(resultado):
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
    
    # Dicionário com os usuários permitidos
    usuarios_permitidos = {
        "Emerson": "1111",
        "Adrielle": "1234"
    }
    
    if st.button("Entrar"):
        # Verifica se o usuário existe no dicionário e se a senha bate
        if usuario in usuarios_permitidos and usuarios_permitidos[usuario] == senha:
            st.session_state.logado = True
            st.session_state.usuario = usuario
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
else:
    # --- APP PRINCIPAL ---
    st.sidebar.title(f"Bem-vindo(a), {st.session_state.usuario}!")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    aba_resolver, aba_relatorios, aba_adicionar = st.tabs(["✍️ Resolver Questões", "📊 Relatórios", "➕ Adicionar Questões"])

    # Carrega os dados diretamente do Supabase
    questoes = carregar_questoes()

    # --- ABA 1: RESOLVER QUESTÕES ---
  # --- ABA 1: RESOLVER QUESTÕES ---
    with aba_resolver:
        st.header("Resolver Questões")
        
        # Puxa histórico para os filtros
        resultados_totais = carregar_resultados()
        meus_resultados = [r for r in resultados_totais if r.get('usuario') == st.session_state.usuario]
        questoes_feitas = set([r['id_questao'] for r in meus_resultados])
        questoes_erradas = set([r['id_questao'] for r in meus_resultados if not r['acertou']])
        
        if not questoes:
            st.warning("Nenhuma questão cadastrada ainda. Vá para a aba 'Adicionar Questões'.")
        else:
            col1, col2, col3 = st.columns(3)
            
            # Filtro de Histórico com o Simulado
            filtro_historico = col1.selectbox(
                "Histórico:", 
                ["Todas", "Nunca feitas", "Já feitas", "Só as que errei", "Simulado (40 questões)"]
            )
            
            # --- LÓGICA DO SIMULADO ---
            if filtro_historico == "Simulado (40 questões)":
                # Congela o simulado na sessão para ele não embaralhar a cada clique
                if 'simulado_gerado' not in st.session_state or st.session_state.get('filtro_atual') != "Simulado (40 questões)":
                    q_inf = [q for q in questoes if q.get("bloco") == "Informática"]
                    q_cg = [q for q in questoes if q.get("bloco") == "Conhecimentos Gerais"]
                    q_ce = [q for q in questoes if q.get("bloco") == "Conhecimentos Específicos"]
                    
                    # Puxa a quantidade exata (ou o máximo que tiver no banco, caso falte)
                    s_inf = random.sample(q_inf, min(10, len(q_inf)))
                    s_cg = random.sample(q_cg, min(10, len(q_cg)))
                    s_ce = random.sample(q_ce, min(20, len(q_ce)))
                    
                    simulado = s_inf + s_cg + s_ce
                    random.shuffle(simulado) # Embaralha a prova inteira
                    st.session_state.simulado_gerado = simulado
                    
                questoes_filtradas = st.session_state.simulado_gerado
                st.session_state.filtro_atual = filtro_historico
                
                # Desativa visualmente os outros filtros, pois o simulado é fixo
                bloco_selecionado = "Todos"
                tema_selecionado = "Todos"
                col2.info("Filtros desativados no modo Simulado.")
                col3.info("Boa sorte na prova!")
                
            # --- LÓGICA NORMAL ---
            else:
                st.session_state.filtro_atual = filtro_historico
                questoes_filtradas = questoes
                
                if filtro_historico == "Nunca feitas":
                    questoes_filtradas = [q for q in questoes_filtradas if q['id'] not in questoes_feitas]
                elif filtro_historico == "Já feitas":
                    questoes_filtradas = [q for q in questoes_filtradas if q['id'] in questoes_feitas]
                elif filtro_historico == "Só as que errei":
                    questoes_filtradas = [q for q in questoes_filtradas if q['id'] in questoes_erradas]

                blocos_disponiveis = list(set([q.get("bloco", "") for q in questoes_filtradas]))
                bloco_selecionado = col2.selectbox("Escolha o Bloco:", ["Todos"] + blocos_disponiveis)
                
                if bloco_selecionado != "Todos":
                    questoes_filtradas = [q for q in questoes_filtradas if q.get("bloco") == bloco_selecionado]
                
                temas_disponiveis = list(set([q.get("tema", "") for q in questoes_filtradas]))
                tema_selecionado = col3.selectbox("Escolha o Tema:", ["Todos"] + temas_disponiveis)
                
                if tema_selecionado != "Todos":
                    questoes_filtradas = [q for q in questoes_filtradas if q.get("tema") == tema_selecionado]

            # --- EXIBIÇÃO DAS QUESTÕES ---
            if not questoes_filtradas:
                st.info("Nenhuma questão encontrada com estes filtros.")
            else:
                st.write(f"**{len(questoes_filtradas)} questões prontas para você.**")
                if filtro_historico == "Simulado (40 questões)" and len(questoes_filtradas) < 40:
                    st.caption("*(Nota: Há menos de 40 questões porque o banco de dados ainda não tem o número exigido para preencher todos os blocos)*")
                st.divider()
                
                for i, q in enumerate(questoes_filtradas):
                    st.markdown(f"**Q{i+1}. ({q['bloco']} - {q['tema']})** {q['enunciado']}")
                    
                    # O retorno do st.radio simples e original!
                    resposta_usuario = st.radio("Alternativas:", q['opcoes'], key=f"radio_{q['id']}", index=None)
                    
                    if st.button("Responder", key=f"btn_{q['id']}"):
                        if resposta_usuario:
                            acertou = (resposta_usuario == q['resposta_correta'])
                            
                            novo_resultado = {
                                "usuario": st.session_state.usuario,
                                "id_questao": q['id'],
                                "bloco": q['bloco'],
                                "tema": q['tema'],
                                "acertou": acertou
                            }
                            salvar_resultado(novo_resultado)
                            
                            # --- RESPOSTAS PERSONALIZADAS DA ADRIELLE ---
                            if acertou:
                                if st.session_state.usuario == "Adrielle":
                                    msg = random.choice(["Foi cagada, aposto, mas acertou!", "Acertou! nunca duvidei ein"])
                                else:
                                    msg = "✅ Resposta Correta!"
                                st.success(msg)
                            else:
                                if st.session_state.usuario == "Adrielle":
                                    msg = random.choice(["errou feio, errou rude.  ", "errou, véia pôde.  "])
                                else:
                                    msg = "❌ Resposta Incorreta."
                                st.error(f"{msg} A correta era: {q['resposta_correta']}")
                                
                            with st.expander("Ver Explicação"):
                                st.write(q['explicacao'])
                        else:
                            st.warning("Selecione uma alternativa antes de responder.")
                    st.divider()
    # --- ABA 2: RELATÓRIOS ---
    with aba_relatorios:
        st.header("Seu Desempenho")
        
        # Puxa os resultados frescos do banco ao abrir a aba
        resultados = carregar_resultados()
        meus_resultados = [r for r in resultados if r['usuario'] == st.session_state.usuario]
        
        if not meus_resultados:
            st.info("Você ainda não respondeu nenhuma questão.")
        else:
            df = pd.DataFrame(meus_resultados)
            
            total_respondidas = len(df)
            total_acertos = df['acertou'].sum()
            taxa_acerto = (total_acertos / total_respondidas) * 100
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Questões Respondidas", total_respondidas)
            col2.metric("Acertos", total_acertos)
            col3.metric("Taxa de Acerto", f"{taxa_acerto:.1f}%")
            
            st.subheader("Desempenho por Bloco")
            # Agrupa os acertos por bloco e calcula a média
            desempenho_bloco = df.groupby('bloco')['acertou'].mean() * 100
            st.bar_chart(desempenho_bloco)

    # --- ABA 3: ADICIONAR QUESTÕES (MÉTODO GEMINI) ---
# --- ABA 3: ADICIONAR QUESTÕES (MÉTODO GEMINI) ---
    with aba_adicionar:
        st.header("Adicionar Questões")
        
        st.write("Defina o Bloco e o Tema para este lote de questões:")
        
        # Lista fixa de blocos
        lista_blocos = [
            "Conhecimentos Específicos", 
            "Conhecimentos Gerais", 
            "Informática"
        ]
        
        # Lista fixa de temas (exatamente como fornecido no edital/tabela)
        lista_temas = [
            "Administração Pública e organização administrativa: princípios constitucionais, administração direta e indireta, poderes e atos administrativos.",
            "Gestão de documentos e arquivística: ciclo de vida dos documentos, classificação, avaliação, temporalidade, arquivamento e digitalização.",
            "Redação oficial: normas e padrões para documentos públicos; linguagem, clareza e objetividade.",
            "Legislação aplicada ao serviço público estadual: estatuto dos servidores, regime jurídico, direitos, deveres e processo administrativo disciplinar.",
            "Gestão de contratos e convênios: celebração, execução, fiscalização, prestação de contas e encerramento.",
            "Orçamento e finanças públicas: estrutura orçamentária, execução da despesa e receita e controle orçamentário.",
            "Compras públicas: Lei n.º 14.133/2021 - modalidades, fases, dispensa e gestão de atas de registro de preços.",
            "Gestão de patrimônio e materiais: catalogação, controle, movimentação e desfazimento de bens públicos.",
            "Tecnologias digitais aplicadas à gestão pública: sistemas integrados, ferramentas de produtividade, portais de transparência e governo eletrônico.",
            "Controle interno, transparência, compliance e integridade na administração pública.",
            "Proteção de dados pessoais no ambiente de trabalho: LGPD, responsabilidades e notificação de incidentes.",
            "Comunicação institucional, atendimento ao público e relações interpessoais no serviço público.",
            "Comunicação pública e atendimento ao cidadão: princípios, linguagem cidadã e qualidade no serviço público.",
            "Gestão de riscos institucionais: identificação, análise, tratamento e monitoramento no setor público.",
            "Processo administrativo estadual: fases, prazos, recursos e princípios norteadores.",
            "Federalismo brasileiro e organização do Estado: distribuição de competências entre União, estados e municípios no âmbito das políticas educacionais e sociais.",
            "Responsabilidade fiscal e social do servidor público: fundamentos e implicações práticas.",
            "Governo aberto, participação social e controle externo: mecanismos, instâncias e responsabilidades.",
            "Sustentabilidade na gestão pública: critérios socioambientais, compras sustentáveis e responsabilidade institucional.",
            "Gestão de crises e continuidade de serviços públicos: fundamentos, protocolos e comunicação institucional.",
            "Noções de internet, intranet e redes de computadores.",
            "Conceitos básicos dos modos de utilização de tecnologias digitais, suas ferramentas, uso e operação de aplicativos e procedimentos de informática.",
            "Conceitos básicos dos modos de utilização de aplicativos para edição de textos, planilhas, apresentações, correio eletrônico, agenda, videoconferência, chat, armazenamento de arquivos.",
            "Ambientes Virtuais de Aprendizagem, formulários eletrônicos, edição de sites utilizando-se a suíte de produtividade Google Workspace.",
            "Noções básicas de edição de imagens e vídeos.",
            "Conceitos e modos de utilização de Sistemas Operacionais, Window 10 e superiores, Chrome OS.",
            "Conceitos e modos de utilização do Adobe Reader e arquivos em formato PDF.",
            "Noções básicas de ferramentas e aplicativos de navegação (Google Chrome, Firefox, Mozilla Firefox, Internet Explorer e Microsoft Edge).",
            "Sítios de busca e pesquisa na internet.",
            "Conceitos de organização e de gerenciamento de informações, arquivos, pastas e programas em ambientes compartilhados.",
            "Conceitos básicos de armazenamento de dados em nuvem.",
            "Noções básicas de segurança da informação, Lei Geral de Proteção de Dados e proteção de sistemas informatizados.",
            "Noções básicas de hardware e software.",
            "Conceitos e modos de utilização de sistemas Operacionais Móveis (Android/iOS)",
            "Constituição da República Federativa do Brasil de 1988: direitos e garantias fundamentais, direitos sociais e disposições constitucionais sobre educação.",
            "Estatuto da Criança e do Adolescente: direito à educação, proteção integral e convivência familiar e comunitária.",
            "Lei de Diretrizes e Bases da Educação Nacional (Lei n.º 9.394/1996) e suas alterações: estrutura, princípios e organização das etapas e modalidades da educação básica.",
            "Plano Nacional de Educação e Plano Estadual de Educação de Santa Catarina: metas, estratégias e avaliação da política educacional.",
            "Lei Complementar Estadual n.º 170/1998: Sistema Estadual de Educação de Santa Catarina.",
            "Marcos legais da educação inclusiva e da educação especial.",
            "Legislação sobre história e cultura afro-brasileira, africana e indígena e sua implementação curricular.",
            "Gestão democrática do ensino público: fundamentos legais e instâncias colegiadas",
            "Regime Jurídico dos Servidores Públicos Civis do Estado de Santa Catarina: direitos, deveres, responsabilidades e regime disciplinar",
            "Plano de carreira do magistério público estadual catarinense.",
            "Base Nacional Comum Curricular: competências gerais, áreas do conhecimento, componentes curriculares e etapas da educação básica.",
            "Proposta Curricular de Santa Catarina: fundamentos históricos e concepções pedagógicas.",
            "Currículo Base da Educação Infantil e do Ensino Fundamental do Território Catarinense: princípios, estrutura e articulação com a BNCC.",
            "Currículo Base do Ensino Médio do Território Catarinense: formação geral básica, itinerários formativos, trilhas de aprofundamento e organização curricular vigente.",
            "Educação Profissional e Tecnológica: diretrizes curriculares nacionais e normas estaduais vigentes.",
            "Integração curricular: interdisciplinaridade, transdisciplinaridade e contextualização do conhecimento.",
            "Avaliação da aprendizagem e avaliação institucional: concepções, indicadores educacionais e uso dos resultados para melhoria da qualidade.",
            "Planejamento educacional e organização do trabalho escolar.",
            "Educação em direitos humanos: princípios, marcos normativos e práticas escolares.",
            "Educação para as relações étnico-raciais: combate ao racismo, valorização da diversidade e implementação curricular.",
            "Educação escolar indígena, quilombola e do campo: especificidades e marcos legais.",
            "Diversidade étnico-racial, de gênero, sexual, religiosa, linguística e sociocultural: reconhecimento e promoção de equidade no contexto escolar.",
            "Inclusão, acessibilidade e Desenho Universal para a Aprendizagem: estratégias e adaptações para a educação para todos.",
            "Convivência escolar, cultura de paz e prevenção às violências: estratégias de mediação e práticas restaurativas.",
            "Saúde mental na escola: competências socioemocionais, bem-estar e trabalho intersetorial.",
            "Proteção de dados pessoais de crianças e adolescentes no contexto educacional.",
            "Cultura digital, letramento digital e cidadania digital: habilidades, responsabilidade e participação crítica.",
            "Uso pedagógico e administrativo de plataformas, ambientes virtuais de aprendizagem e recursos educacionais abertos.",
            "Ensino híbrido e educação a distância: modelos, regulamentação e aplicações.",
            "Inteligência Artificial na educação: aplicações éticas e potencial transformador no ensino e na gestão.",
            "Segurança da informação, proteção de dados pessoais (Lei Geral de Proteção de Dados - LGPD) e governança digital no ambiente educacional.",
            "Inovações científicas e tecnológicas contemporâneas e seus impactos no mundo do trabalho e na sociedade.",
            "Princípios constitucionais da Administração Pública: legalidade, impessoalidade, moralidade, publicidade e eficiência.",
            "Ética no serviço público: deveres, conflito de interesses, integridade, transparência e responsabilidade.",
            "Lei de Acesso à Informação: transparência ativa, passiva e sigilo.",
            "Relações humanas no trabalho: comunicação, trabalho em equipe e resolução de conflitos.",
            "Aspectos históricos,culturais, geográficos, sociais, políticos e econômicos de Santa Catarina e do Brasil contemporâneo relevantes para a compreensão das dinâmicas educacionais e administrativas."
        ]

        col1, col2 = st.columns(2)
        novo_bloco = col1.selectbox("Selecione o Bloco:", lista_blocos)
        novo_tema = col2.selectbox("Selecione o Tema:", lista_temas)
        
        st.markdown("""
        Peça para a IA gerar questões no formato JSON e cole na caixa abaixo. 
        O formato esperado é uma lista `[...]` contendo as questões.
        """)
        
        json_input = st.text_area("Cole o JSON gerado aqui:", height=300)
        
        if st.button("Importar Questões"):
            if json_input.strip() == "":
                st.warning("⚠️ Cole o JSON antes de importar.")
            else:
                try:
                    novas_questoes = json.loads(json_input)
                    if isinstance(novas_questoes, list):
                        for nq in novas_questoes:
                            # Gera o ID único
                            nq['id'] = str(uuid.uuid4())
                            
                            # AQUI ESTÁ A MÁGICA: Força a questão a usar as opções dos selects
                            nq['bloco'] = novo_bloco
                            nq['tema'] = novo_tema
                        
                        salvar_questoes(novas_questoes)
                        st.success(f"✅ {len(novas_questoes)} questões vinculadas a '{novo_bloco}' cadastradas com sucesso!")
                    else:
                        st.error("O JSON deve ser uma lista de questões [ { ... }, { ... } ].")
                except json.JSONDecodeError:
                    st.error("Erro ao ler o JSON. Verifique se copiou corretamente e se não há texto fora das chaves.")
                except Exception as e:
                    st.error(f"Erro ao salvar no banco de dados: {e}")