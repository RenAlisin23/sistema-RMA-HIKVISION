import streamlit as st
from supabase import create_client
import pandas as pd

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="RMA Hikvision Control", layout="wide", page_icon="📦")

# 2. DISEÑO CSS PARA BLINDAR LA APP (OCULTA MANAGE APP, TOOLBAR Y DECORACIÓN)
st.markdown("""
    <style>
    /* OCULTAR TODOS LOS ELEMENTOS DE DESARROLLO Y GESTIÓN */
    header { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    
    /* ELIMINAR EL BOTÓN 'MANAGE APP' Y 'DEPLOY' */
    button[title="View source on GitHub"] { display: none !important; }
    .stDeployButton { display: none !important; }
    #stManageAppButton { display: none !important; }
    [data-testid="stManageAppButton"] { display: none !important; }

    /* ESTILO DARK INDUSTRIAL */
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    h1, h2, h3, p, label { color: #e6edf3 !important; font-family: 'Inter', sans-serif; }
    
    /* BARRA LATERAL */
    [data-testid="stSidebar"] { background-color: #010409; border-right: 2px solid #eb1c24; }
    
    /* TARJETAS DE MÉTRICAS */
    [data-testid="stMetric"] {
        background-color: #161b22;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #30363d;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.5);
    }
    [data-testid="stMetricValue"] { color: #58a6ff !important; }

    /* BOTONES ROJO SANGRE */
    .stButton>button {
        background: #8b0000;
        color: white !important;
        border-radius: 8px !important;
        border: 1px solid #eb1c24 !important;
        font-weight: bold;
    }
    .stButton>button:hover { background: #eb1c24; }
    </style>
    """, unsafe_allow_html=True)

# 3. SISTEMA DE LOGIN INTEGRADO
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

def pantalla_login():
    c1, c2, c3 = st.columns([1,2,1])
    with col2 := c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=350)
        st.markdown("## 🔐 Acceso Restringido")
        with st.form("login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("ENTRAR"):
                if u == "admin" and p == "Hik13579":
                    st.session_state['autenticado'] = True
                    st.rerun()
                else:
                    st.error("Acceso denegado")

if not st.session_state['autenticado']:
    pantalla_login()
    st.stop()

# 4. CONEXIÓN (Solo después del login)
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# 5. BARRA LATERAL (REGISTRO)
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=150)
    st.markdown("### ➕ Registrar RMA")
    with st.form("reg", clear_on_submit=True):
        f_rma = st.text_input("Número RMA")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn  = st.text_input("S/N")
        f_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        f_com = st.text_area("Comentarios")
        if st.form_submit_button("GUARDAR"):
            if f_rma and f_emp:
                data = {"rma_number": f_rma, "empresa": f_emp, "modelo": f_mod, 
                        "serial_number": f_sn, "informacion": f_est, 
                        "comentarios": f_com, "enviado": "NO", "fedex_number": ""}
                supabase.table("inventario_rma").insert(data).execute()
                st.success("✅ Guardado")
                st.rerun()
    
    st.markdown("---")
    if st.button("🚪 Salir"):
        st.session_state['autenticado'] = False
        st.rerun()

# 6. CUERPO PRINCIPAL
st.markdown("# 📦 Panel de Control RMA")

# Carga de datos
res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

if not df.empty:
    # Métricas
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("TOTAL", len(df))
    c_m2.metric("EN TALLER", len(df[df['informacion'] == 'En proceso']))
    c_m3.metric("LISTOS", len(df[df['informacion'] == 'FINALIZADO']))

    st.markdown("---")

    # 7. EDITOR POR ID (BUSCAR Y ACTUALIZAR)
    st.markdown("### 🛠️ Editor Maestro")
    with st.expander("📝 SELECCIONAR REGISTRO POR ID PARA MODIFICAR"):
        # Lista desplegable con ID y RMA
        opciones = ["ID: " + str(r['id']) + " | RMA: " + str(r['rma_number']) for r in res.data]
        sel_label = st.selectbox("Buscar registro:", ["---"] + opciones)
        
        if sel_label != "---":
            id_selecionado = int(sel_label.split("|")[0].replace("ID: ", "").strip())
            fila = df[df['id'] == id_selecionado].iloc[0]
            
            with st.form("edit_id"):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    n_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"], 
                                       index=0 if fila['informacion'] == "En proceso" else 1)
                    n_env = st.selectbox("Alerta (enviado)", ["NO", "YES"], 
                                       index=0 if fila['enviado'] == "NO" else 1)
                with e_col2:
                    n_fedex = st.text_input("Guía FedEx", value=str(fila.get('fedex_number', '')))
                    n_com = st.text_area("Notas", value=fila['comentarios'])
                
                if st.form_submit_button("ACTUALIZAR REGISTRO #" + str(id_selecionado)):
                    upd_data = {"informacion": n_est, "enviado": n_env, 
                                "comentarios": n_com, "fedex_number": n_fedex}
                    supabase.table("inventario_rma").update(upd_data).eq("id", id_selecionado).execute()
                    st.success("✅ Registro actualizado")
                    st.rerun()

    st.markdown("---")

    # 8. VISUALIZACIÓN
    busq = st.text_input("🔍 Filtrar tabla...", placeholder="RMA, Empresa o S/N")
    df_f = df[df.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)] if busq else df

    def color_est(v):
        if v == 'FINALIZADO': return 'background-color: #062612; color: #34ee71; font-weight: bold;'
        return 'background-color: #2b2106; color: #eec234;'

    st.dataframe(
        df_f[["id", "rma_number", "empresa", "modelo", "informacion", "fedex_number", "comentarios"]].style.applymap(color_est, subset=['informacion']),
        use_container_width=True, hide_index=True,
        column_config={"id": "ID", "fedex_number": "📦 FedEx", "informacion": "Estado"}
    )
else:
    st.info("Sin datos para mostrar.")
