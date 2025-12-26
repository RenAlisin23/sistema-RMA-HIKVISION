import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="RMA Hikvision", layout="wide", page_icon="📦")

# 2. DISEÑO CSS PARA BLINDAR LA APP
st.markdown("""
    <style>
    header { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    [data-testid="stManageAppButton"] { display: none !important; }
    .stDeployButton { display: none !important; }

    .stApp { background-color: #0d1117; color: #c9d1d9; }
    h1, h2, h3, p, label { color: #e6edf3 !important; font-family: 'Inter', sans-serif; }
    
    [data-testid="stSidebar"] { background-color: #010409; border-right: 2px solid #eb1c24; }
    
    [data-testid="stMetric"] {
        background-color: #161b22;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #30363d;
    }

    .stButton>button {
        background: #8b0000;
        color: white !important;
        border-radius: 8px !important;
        border: 1px solid #eb1c24 !important;
        font-weight: bold;
        width: 100%;
    }
    .stButton>button:hover { background: #eb1c24; }
    </style>
    """, unsafe_allow_html=True)

# 3. SISTEMA DE LOGIN
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

def pantalla_login():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=350)
        st.markdown("## Acceso Restringido")
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

# 4. CONEXIÓN
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# 5. Registro para nuevas partes
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=150)
    st.markdown("### ➕ Registrar RMA")
    with st.form("reg", clear_on_submit=True):
        f_rma = st.text_input("Número RMA")
        f_ticket = st.text_input("Nº Ticket")
        f_rq = st.text_input("Nº RQ")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn  = st.text_input("S/N")
        f_desc = st.text_area("Ingrese partes del modelo aplicadas")
        f_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        f_com = st.text_area("Comentarios")
        
        if st.form_submit_button("GUARDAR"):
            if f_rma and f_emp:
                data = {
                    "rma_number": f_rma, 
                    "n_ticket": f_ticket,
                    "n_rq": f_rq,
                    "empresa": f_emp, 
                    "modelo": f_mod, 
                    "serial_number": f_sn, 
                    "descripcion": f_desc,
                    "informacion": f_est, 
                    "comentarios": f_com, 
                    "enviado": "NO", 
                    "fedex_number": ""
                }
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
try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    if not df_raw.empty:
        df_raw['id_amigable'] = range(len(df_raw), 0, -1)
        df = df_raw
    else:
        df = pd.DataFrame()
except:
    df = pd.DataFrame()

if not df.empty:
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("TOTAL", len(df))
    c_m2.metric("EN PROCESO", len(df[df['informacion'] == 'En proceso']))
    c_m3.metric("FINALIZADOS", len(df[df['informacion'] == 'FINALIZADO']))

    st.markdown("---")

    # 7. EDITOR
    st.markdown("### 🛠️ Edición de casos")
    with st.expander("📝 Buscador de casos para actualizar"):
        opciones = [f"Nº {r['id_amigable']} | RMA: {r['rma_number']} | {r['empresa']}" for _, r in df.iterrows()]
        sel_label = st.selectbox("Seleccionar:", ["---"] + opciones)
        
        if sel_label != "---":
            num_amigable = int(sel_label.split("|")[0].replace("Nº ", "").strip())
            fila = df[df['id_amigable'] == num_amigable].iloc[0]
            id_tecnico = fila['id'] 
            
            with st.form("edit_id"):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    n_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"], 
                                       index=0 if fila['informacion'] == "En proceso" else 1)
                    n_env = st.selectbox("Alerta (enviado)", ["NO", "YES"], 
                                       index=0 if fila['enviado'] == "NO" else 1)
                with e_col2:
                    n_fedex = st.text_input("Guía FedEx", value=str(fila.get('fedex_number', '')))
                    n_desc = st.text_area("Descripción", value=str(fila.get('descripcion', '')))
                
                n_com = st.text_area("Notas/Comentarios", value=str(fila.get('comentarios', '')))
                
                if st.form_submit_button(f"ACTUALIZAR REGISTRO Nº {num_amigable}"):
                    upd_data = {"informacion": n_est, "enviado": n_env, 
                                "comentarios": n_com, "fedex_number": n_fedex, "descripcion": n_desc}
                    supabase.table("inventario_rma").update(upd_data).eq("id", id_tecnico).execute()
                    st.success(f"Registro Nº {num_amigable} actualizado")
                    st.rerun()

    st.markdown("---")

    # 8. TABLA FINAL
    busq = st.text_input("🔍 Filtrar tabla...", placeholder="RMA, Ticket, Empresa o S/N")
    df_f = df[df.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)] if busq else df

    def color_est(v):
        # Colores para la columna 'informacion' (Estado)
        if v == 'FINALIZADO': 
            return 'background-color: #062612; color: #34ee71; font-weight: bold;'
        if v == 'En proceso':
            return 'background-color: #2b2106; color: #eec234;'
    
        # Colores para la columna 'enviado'
        if v == 'YES':
            return 'background-color: #1a1a40; color: #50fa7b; font-weight: bold;' # Azul oscuro con verde
        if v == 'NO':
            return 'background-color: #3e0b0b; color: #ff5555;' # Rojo oscuro con rojo claro
        
        return ''

    st.dataframe(
        df_f[["id_amigable","n_rq","n_ticket", "empresa", "modelo", "descripcion","comentarios","enviado","informacion", "fedex_number","fecha_registro"]].style.applymap(color_est, subset=['informacion',"enviado"]),
        use_container_width=True, hide_index=True,
        column_config={
            "id_amigable": "Nº", 
            "n_rq": "Número de RQ",
            "n_ticket": "Ticket",
            "fedex_number": "📦 FedEx", 
            "informacion": "Estado",
            "enviado": "Enviado",
            "descripcion": "Descripción",
            "comentarios": "Comentarios",
            "fecha_registro": "Fecha de Registro"
        }
    )
else:
    st.info("No hay datos registrados.")
