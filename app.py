import streamlit as st
from supabase import create_client
import pandas as pd

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="HIK-RMA System", layout="wide", page_icon="📦")

# 2. VISUALIZACION DE LA PAGINA
st.markdown("""
    <style>
    /* OCULTAR ELEMENTOS DE STREAMLIT (Lápiz, GitHub, Share) */
    header { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stToolbar"] { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }
    
    /* FONTO Y TEXTOS */
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    h1, h2, h3, p, label { color: #e6edf3 !important; font-family: 'Inter', sans-serif; }
    
    /* BARRA LATERAL */
    [data-testid="stSidebar"] { background-color: #010409; border-right: 2px solid #eb1c24; }
    
    /* TARJETAS DE MÉTRICAS */
    [data-testid="stMetric"] {
        background-color: #161b22;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.5);
        border: 1px solid #30363d;
    }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: bold; }

    /* INPUTS */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
        border: 1px solid #30363d !important;
    }

    /* BOTONES */
    .stButton>button {
        background: #8b0000;
        color: #f0f6fc !important;
        border-radius: 8px !important;
        border: 1px solid #eb1c24 !important;
        width: 100%;
        font-weight: bold;
    }
    .stButton>button:hover { background: #eb1c24; border: 1px solid #ff4d4d !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. SISTEMA DE AUTENTICACIÓN 
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

def login_screen():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=350)
        st.markdown("## 🔐 Identificador de Usuario")
        with st.form("login_form"):
            user = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("ACCEDER AL SISTEMA"):
                # OJO PARA EL INGRESO
                if user == "admin" and password == "Hik13579":
                    st.session_state['autenticado'] = True
                    st.rerun()
                else:
                    st.error("❌ Usuario o clave incorrectos")

# VERIFICAR SI ESTÁ LOGUEADO
if not st.session_state['autenticado']:
    login_screen()
    st.stop()

# 4. CONEXIÓN A BASE DE DATOS 
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# 5. BARRA LATERAL
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=150)
    st.markdown("### ➕ Nuevo Ingreso")
    with st.form("form_registro", clear_on_submit=True):
        rma = st.text_input("RMA Number")
        empresa = st.text_input("Empresa")
        n_rq = st.text_input("Nº RQ")
        ticket = st.text_input("Nº Ticket")
        modelo = st.text_input("Modelo")
        sn = st.text_input("Serial Number")
        info = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        coments = st.text_area("Comentarios")
        if st.form_submit_button("GUARDAR EQUIPO"):
            if rma and empresa:
                nuevo = {
                    "rma_number": rma, "n_rq": n_rq, "empresa": empresa,
                    "n_ticket": ticket, "modelo": modelo, "serial_number": sn,
                    "informacion": info, "comentarios": coments, "enviado": "NO",
                    "fedex_number": ""
                }
                supabase.table("inventario_rma").insert(nuevo).execute()
                st.success("✅ Registrado con éxito")
                st.rerun()
    
    st.markdown("---")
    if st.button("🚪 Cerrar Sesión"):
        st.session_state['autenticado'] = False
        st.rerun()

# 6. PANEL PRINCIPAL
st.markdown("# 📦 RMA Control Center")

# Carga de Datos
try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
except:
    df = pd.DataFrame()

if not df.empty:
    # Métricas
    m1, m2, m3 = st.columns(3)
    m1.metric("EQUIPOS TOTALES", len(df))
    m2.metric("EN TALLER", len(df[df['informacion'] == 'En proceso']))
    m3.metric("FINALIZADOS", len(df[df['informacion'] == 'FINALIZADO']))

    st.markdown("---")

    # 7. PANEL DE EDICIÓN
    st.markdown("### 🛠️ Modificar Registro")
    with st.expander("📝 EDITAR ESTADO / COMENTARIOS / FEDEX", expanded=False):
        rma_list = df['rma_number'].tolist()
        rma_sel = st.selectbox("Selecciona RMA para modificar:", ["---"] + rma_list)
        
        if rma_sel != "---":
            fila = df[df['rma_number'] == rma_sel].iloc[0]
            with st.form("form_edicion"):
                c1, c2 = st.columns(2)
                with c1:
                    edit_info = st.selectbox("Estado Actual", ["En proceso", "FINALIZADO"], 
                                           index=0 if fila['informacion'] == "En proceso" else 1)
                    edit_enviado = st.selectbox("Detener Alerta (enviado)", ["NO", "YES"], 
                                              index=0 if fila['enviado'] != "YES" else 1)
                with c2:
                    edit_fedex = st.text_input("Número FedEx", value=str(fila.get('fedex_number', '')))
                    edit_coments = st.text_area("Notas Actualizadas", value=fila['comentarios'])
                
                if st.form_submit_button("ACTUALIZAR DATOS"):
                    upd = {"informacion": edit_info, "enviado": edit_enviado, 
                           "comentarios": edit_coments, "fedex_number": edit_fedex}
                    supabase.table("inventario_rma").update(upd).eq("rma_number", rma_sel).execute()
                    st.success("✅ Actualizado!")
                    st.rerun()

    st.markdown("---")

    # 8. BUSCADOR Y TABLA
    busqueda = st.text_input("🔍 Filtro de búsqueda", placeholder="Escribe RMA, Empresa o Serial...")
    if busqueda:
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_mostrar = df[mask]
    else:
        df_mostrar = df

    def style_status(val):
        if val == 'FINALIZADO': return 'background-color: #062612; color: #34ee71; font-weight: bold;'
        return 'background-color: #2b2106; color: #eec234;'

    cols = ["rma_number", "empresa", "modelo", "serial_number", "informacion", "fedex_number", "comentarios", "fecha_registro"]
    st.dataframe(
        df_mostrar[cols].style.applymap(style_status, subset=['informacion']),
        use_container_width=True, hide_index=True,
        column_config={
            "comentarios": st.column_config.TextColumn("Notas", width="medium"),
            "fedex_number": "📦 FedEx",
            "fecha_registro": st.column_config.DatetimeColumn("Ingreso", format="DD/MM/YY HH:mm")
        }
    )
else:
    st.info("No hay datos en la base de datos.")
