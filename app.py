import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# 1. CONFIGURACIÓN Y ESTILO HIKVISION
st.set_page_config(page_title="RMA Hikvision", layout="wide")

st.markdown("""
    <style>
    header { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    h1, h2, h3, p, label { color: #e6edf3 !important; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #010409; border-right: 2px solid #eb1c24; }
    .stButton>button {
        background: #8b0000; color: white !important;
        border-radius: 8px !important; border: 1px solid #eb1c24 !important;
        font-weight: bold; width: 100%;
    }
    .stButton>button:hover { background: #eb1c24; }
    </style>
    """, unsafe_allow_html=True)

# 2. LOGIN CON LOGO
if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'rol': None})

def pantalla_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=300)
        st.subheader("Acceso al Sistema")
        with st.form("login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("ENTRAR"):
                if u == "admin" and p == "Hik13579":
                    st.session_state.update({'autenticado': True, 'rol': 'admin'})
                    st.rerun()
                elif u == "user" and p == "Hik12345":
                    st.session_state.update({'autenticado': True, 'rol': 'tecnico'})
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")

if not st.session_state['autenticado']:
    pantalla_login()
    st.stop()

# 3. CONEXIÓN (El puente necesario para Supabase)
@st.cache_resource
def conectar_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = conectar_db()

# 4. SIDEBAR (Registro y Logo)
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=120)
    st.markdown(f"**Sesión:** {st.session_state['rol'].upper()}")
    st.markdown("---")
    with st.form("nuevo_rma", clear_on_submit=True):
        f_rma = st.text_input("Número RMA")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn  = st.text_input("S/N")
        f_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        if st.form_submit_button("GUARDAR REGISTRO"):
            if f_rma and f_emp:
                supabase.table("inventario_rma").insert({
                    "rma_number": f_rma, "empresa": f_emp, "modelo": f_mod, 
                    "serial_number": f_sn, "informacion": f_est, "enviado": "NO"
                }).execute()
                st.rerun()
    if st.button("Cerrar Sesión"):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 5. CARGA Y LIMPIEZA DE DATOS
try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    if not df.empty:
        df['fecha_registro'] = pd.to_datetime(df['fecha_registro']).dt.date
        df['Nº'] = range(len(df), 0, -1)
except:
    df = pd.DataFrame()

# 6. PANEL PRINCIPAL
st.title("📦 Gestión RMA")

if not df.empty:
    # Botón Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.drop(columns=['id']).to_excel(writer, index=False)
    st.download_button("📥 Descargar Excel", output.getvalue(), "reporte_rma.xlsx")

    # EDICIÓN INTUITIVA (Buscador)
    with st.expander("🛠️ Actualizar o Eliminar Casos"):
        opciones = [f"Nº {r['Nº']} | {r['rma_number']} | {r['empresa']}" for _, r in df.iterrows()]
        seleccion = st.selectbox("Buscar caso:", ["---"] + opciones)
        
        if seleccion != "---":
            num_id = int(seleccion.split("|")[0].replace("Nº ", "").strip())
            fila = df[df['Nº'] == num_id].iloc[0]
            
            with st.form("edit"):
                c1, c2 = st.columns(2)
                n_est = c1.selectbox("Estado", ["En proceso", "FINALIZADO"], index=0 if fila['informacion'] == "En proceso" else 1)
                n_env = c1.selectbox("Enviado", ["NO", "YES"], index=0 if fila['enviado'] == "NO" else 1)
                n_fedex = c2.text_input("FedEx", value=str(fila.get('fedex_number', '')))
                n_com = st.text_area("Comentarios", value=str(fila.get('comentarios', '')))
                
                col_btn1, col_btn2 = st.columns([3, 1])
                if col_btn1.form_submit_button("ACTUALIZAR"):
                    supabase.table("inventario_rma").update({"informacion": n_est, "enviado": n_env, "comentarios": n_com, "fedex_number": n_fedex}).eq("id", fila['id']).execute()
                    st.rerun()
                
                if st.session_state['rol'] == 'admin':
                    if col_btn2.form_submit_button("🗑️ BORRAR"):
                        supabase.table("inventario_rma").delete().eq("id", fila['id']).execute()
                        st.rerun()

    # TABLA FINAL
    busq = st.text_input("🔍 Filtrar...")
    df_f = df[df.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)] if busq else df
    
    st.dataframe(
        df_f[["Nº", "fecha_registro", "rma_number", "empresa", "modelo", "enviado", "informacion", "fedex_number"]],
        use_container_width=True, hide_index=True
    )
else:
    st.info("Sin datos.")
