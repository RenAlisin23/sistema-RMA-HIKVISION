import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="RMA Hikvision", layout="wide", page_icon="📦")

# 2. DISEÑO CSS (Tu estilo original)
st.markdown("""
    <style>
    header { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stToolbar"] { display: none !important; }
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

# 3. LOGIN (Mantenemos tu lógica de Admin/User)
if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'rol': None})

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
                    st.session_state.update({'autenticado': True, 'rol': 'admin'})
                    st.rerun()
                elif u == "user" and p == "Hik12345":
                    st.session_state.update({'autenticado': True, 'rol': 'tecnico'})
                    st.rerun()
                else:
                    st.error("Acceso denegado")

if not st.session_state['autenticado']:
    pantalla_login()
    st.stop()

# 4. CONEXIÓN (Necesaria para que Supabase funcione)
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# 5. REGISTRO (Tus campos exactos)
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=150)
    st.markdown(f"### 👤 {st.session_state['rol'].upper()}")
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
                    "rma_number": f_rma, "n_ticket": f_ticket, "n_rq": f_rq,
                    "empresa": f_emp, "modelo": f_mod, "serial_number": f_sn, 
                    "descripcion": f_desc, "informacion": f_est, 
                    "comentarios": f_com, "enviado": "NO", "fedex_number": ""
                }
                supabase.table("inventario_rma").insert(data).execute()
                st.success("✅ Guardado")
                st.rerun()

    if st.button("🚪 Salir"):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 6. CUERPO PRINCIPAL
st.markdown("# 📦 Panel de Control RMA")

try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    if not df_raw.empty:
        # LIMPIEZA DE FECHA PARA QUE SE VEA BIEN
        df_raw['fecha_registro'] = pd.to_datetime(df_raw['fecha_registro']).dt.date
        # TU ID AMIGABLE
        df_raw['id_amigable'] = range(len(df_raw), 0, -1)
        df = df_raw
    else:
        df = pd.DataFrame()
except:
    df = pd.DataFrame()

if not df.empty:
    # EXCEL (Añadido)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.drop(columns=['id'], errors='ignore').to_excel(writer, index=False)
    st.download_button("📥 Descargar Reporte Excel", output.getvalue(), "reporte_rma.xlsx")

    st.markdown("---")

    # 7. EDITOR (Tu lógica de buscador con id_amigable)
    st.markdown("### 🛠️ Edición de casos")
    with st.expander("📝 Buscador de casos para actualizar"):
        opciones = [f"Nº {r['id_amigable']} | RMA: {r['rma_number']} | {r['empresa']}" for _, r in df.iterrows()]
        sel_label = st.selectbox("Seleccionar:", ["---"] + opciones)
        
        if sel_label != "---":
            num_amigable = int(sel_label.split("|")[0].replace("Nº ", "").strip())
            fila = df[df['id_amigable'] == num_amigable].iloc[0]
            
            with st.form("edit_id"):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    n_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"], 
                                       index=0 if fila['informacion'] == "En proceso" else 1)
                    n_env = st.selectbox("Enviado", ["NO", "YES"], 
                                       index=0 if fila['enviado'] == "NO" else 1)
                with e_col2:
                    n_fedex = st.text_input("Guía FedEx", value=str(fila.get('fedex_number', '')))
                    n_desc = st.text_area("Descripción", value=str(fila.get('descripcion', '')))
                
                n_com = st.text_area("Notas/Comentarios", value=str(fila.get('comentarios', '')))
                
                c_act, c_borr = st.columns([3, 1])
                if c_act.form_submit_button("ACTUALIZAR REGISTRO"):
                    upd = {"informacion": n_est, "enviado": n_env, "comentarios": n_com, "fedex_number": n_fedex, "descripcion": n_desc}
                    supabase.table("inventario_rma").update(upd).eq("id", fila['id']).execute()
                    st.rerun()
                
                # ELIMINAR SOLO PARA ADMIN
                if st.session_state['rol'] == 'admin':
                    if c_borr.form_submit_button("🗑️ BORRAR"):
                        supabase.table("inventario_rma").delete().eq("id", fila['id']).execute()
                        st.rerun()

    st.markdown("---")

    # 8. TABLA (Tu visualización con colores)
    busq = st.text_input("🔍 Filtrar tabla...")
    df_f = df[df.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)] if busq else df

    def color_est(v):
        if v == 'FINALIZADO': return 'background-color: #062612; color: #34ee71; font-weight: bold;'
        if v == 'En proceso': return 'background-color: #2b2106; color: #eec234;'
        if v == 'YES': return 'background-color: #1a1a40; color: #50fa7b; font-weight: bold;'
        if v == 'NO': return 'background-color: #3e0b0b; color: #ff5555;'
        return ''

    st.dataframe(
        df_f[["id_amigable","n_rq","n_ticket", "empresa", "modelo", "descripcion","comentarios","enviado","informacion", "fedex_number","fecha_registro"]].style.applymap(color_est, subset=['informacion',"enviado"]),
        use_container_width=True, hide_index=True,
        column_config={"id_amigable": "Nº", "fedex_number": "📦 FedEx", "informacion": "Estado"}
    )
else:
    st.info("No hay datos registrados.")
