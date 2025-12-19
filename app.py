import streamlit as st
from supabase import create_client
import pandas as pd

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="RMA Hikvision | Control Center", layout="wide", page_icon="📦")

# 2. CONEXIÓN A BASE DE DATOS
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        st.error("⚠️ Error de conexión.")
        return None

supabase = init_connection()

# 3. DISEÑO "INDUSTRIAL DARK" 
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    h1, h2, h3, p, label { color: #e6edf3 !important; }
    
    [data-testid="stSidebar"] { background-color: #010409; border-right: 2px solid #eb1c24; }
    
    /* Tarjetas de métricas */
    [data-testid="stMetric"] {
        background-color: #161b22;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.5);
        border: 1px solid #30363d;
    }
    
    /* Inputs y Selects */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
        border: 1px solid #30363d !important;
    }

    /* Botón Rojo */
    .stButton>button {
        background: #8b0000;
        color: #f0f6fc !important;
        border-radius: 8px !important;
        border: 1px solid #eb1c24 !important;
        width: 100%;
    }
    .stButton>button:hover { background: #eb1c24; }

    /* Estilo para el Expander de Edición */
    .stExpander { border: 1px solid #eb1c24 !important; background-color: #0d1117 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- BARRA LATERAL: REGISTRO ---
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=180)
    st.markdown("## ➕ Registro de Equipo")
    with st.form("form_registro", clear_on_submit=True):
        rma = st.text_input("RMA Number")
        empresa = st.text_input("Empresa")
        n_rq = st.text_input("Nº RQ")
        ticket = st.text_input("Nº Ticket")
        modelo = st.text_input("Modelo")
        sn = st.text_input("Serial Number")
        info = st.selectbox("Estado Inicial", ["En proceso", "FINALIZADO"])
        coments = st.text_area("Comentarios Iniciales")
        if st.form_submit_button("GUARDAR NUEVO"):
            if rma and empresa:
                nuevo = {"rma_number": rma, "n_rq": n_rq, "empresa": empresa, "n_ticket": ticket, 
                         "modelo": modelo, "serial_number": sn, "informacion": info, 
                         "comentarios": coments, "enviado": "NO", "fedex_number": ""}
                supabase.table("inventario_rma").insert(nuevo).execute()
                st.success("✅ Registrado")
                st.rerun()

# --- PANEL PRINCIPAL ---
st.title("🛡️ HIK-RMA Control Center")

# 4. CARGA DE DATOS
try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
except:
    df = pd.DataFrame()

if not df.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("TOTAL REGISTROS", len(df))
    m2.metric("PENDIENTES HQ", len(df[df['informacion'] == 'En proceso']))
    m3.metric("LISTOS / OK", len(df[df['informacion'] == 'FINALIZADO']))

    st.markdown("---")

    # --- SECCIÓN 5: MODIFICAR EQUIPOS (LO NUEVO) ---
    st.markdown("### 🛠️ Actualizar Información de Equipo")
    with st.expander("ABRIR PANEL DE EDICIÓN", expanded=False):
        # Buscador por RMA para editar
        opciones_rma = df['rma_number'].tolist()
        rma_sel = st.selectbox("Busca el RMA para editar:", ["---"] + opciones_rma)
        
        if rma_sel != "---":
            # Obtener datos actuales de la fila elegida
            fila = df[df['rma_number'] == rma_sel].iloc[0]
            
            with st.form("form_edicion"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    edit_info = st.selectbox("Estado", ["En proceso", "FINALIZADO"], 
                                           index=0 if fila['informacion'] == "En proceso" else 1)
                    edit_enviado = st.selectbox("¿Detener Alertas? (YES/NO)", ["NO", "YES"], 
                                              index=0 if fila['enviado'] != "YES" else 1)
                with c2:
                    # Usamos .get por si la columna fedex no existe aún
                    edit_fedex = st.text_input("Nº FedEx / Guía", value=str(fila.get('fedex_number', '')))
                with c3:
                    edit_coments = st.text_area("Comentarios del Técnico", value=fila['comentarios'])
                
                if st.form_submit_button("ACTUALIZAR REGISTRO"):
                    upd = {
                        "informacion": edit_info,
                        "enviado": edit_enviado,
                        "comentarios": edit_coments,
                        "fedex_number": edit_fedex
                    }
                    supabase.table("inventario_rma").update(upd).eq("rma_number", rma_sel).execute()
                    st.success(f"✅ RMA {rma_sel} actualizado")
                    st.rerun()

    st.markdown("---")

    # --- SECCIÓN 6: BUSCADOR Y TABLA ---
    busqueda = st.text_input("🔍 Buscador General", placeholder="Filtra por RMA, Empresa, S/N o FedEx...")
    
    if busqueda:
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_mostrar = df[mask]
    else:
        df_mostrar = df

    def highlight_status(val):
        if val == 'FINALIZADO': return 'background-color: #062612; color: #34ee71; font-weight: bold;'
        return 'background-color: #2b2106; color: #eec234;'

    columnas_ver = ["rma_number", "empresa", "modelo", "serial_number", "informacion", "fedex_number", "comentarios", "fecha_registro"]
    
    st.dataframe(
        df_mostrar[columnas_ver].style.applymap(highlight_status, subset=['informacion']),
        use_container_width=True, hide_index=True,
        column_config={
            "comentarios": st.column_config.TextColumn("Notas", width="large"),
            "fedex_number": "📦 FedEx #",
            "fecha_registro": st.column_config.DatetimeColumn("Entrada", format="DD/MM/YY HH:mm")
        }
    )
else:
    st.info("No hay registros.")
