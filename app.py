import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Gestión RMA Hikvision", layout="wide")

# 2. CSS DE ALTO NIVEL
st.markdown("""
    <style>
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stApp { background-color: #0d1117; color: #e6edf3; }
    
    /* Estilo de Tarjetas de Métricas */
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 15px !important;
    }
    
    /* Estilo de la Sidebar */
    [data-testid="stSidebar"] {
        background-color: #010409;
        border-right: 1px solid #30363d;
    }

    /* Botones Profesionales */
    .stButton>button {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
        font-weight: 500;
    }
    .stButton>button:hover {
        border-color: #eb1c24;
        color: #eb1c24;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXIÓN Y LOGIN
if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'rol': None})

def pantalla_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=280)
        st.markdown("<h2 style='text-align: center;'>Portal de Gestión RMA</h2>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("INICIAR SESIÓN"):
                if u == "admin" and p == "Hik13579":
                    st.session_state.update({'autenticado': True, 'rol': 'admin'})
                    st.rerun()
                elif u == "user" and p == "Hik12345":
                    st.session_state.update({'autenticado': True, 'rol': 'user'})
                    st.rerun()
                else: st.error("Credenciales incorrectas")

if not st.session_state['autenticado']:
    pantalla_login()
    st.stop()

@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

def preparar_excel(df):
    # Solo exportamos datos útiles para el reporte
    columnas_basura = ['id', 'id_amigable', 'Seleccionar']
    df_clean = df.drop(columns=[c for c in columnas_basura if c in df.columns])
    
    # Renombrar columnas para el Excel Profesional
    renombrar_excel = {
        "rma_number": "RMA", "n_ticket": "Ticket", "n_rq": "RQ",
        "empresa": "Empresa", "modelo": "Modelo", "serial_number": "S/N",
        "informacion": "Estado", "enviado": "Enviado", "comentarios": "Comentarios"
    }
    df_clean = df_clean.rename(columns=renombrar_excel)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_clean.to_excel(writer, index=False, sheet_name='Reporte_RMA')
    return output.getvalue()

# 4. SIDEBAR (Registro)
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=140)
    st.markdown(f"**Usuario:** `{st.session_state['rol'].upper()}`")
    
    with st.form("nuevo_registro"):
        st.markdown("### 📝 Registrar Equipo")
        f_rma = st.text_input("Número RMA")
        f_ticket = st.text_input("Ticket")
        f_rq = st.text_input("RQ")
        f_emp = st.text_input("Empresa / Cliente")
        f_mod = st.text_input("Modelo del Equipo")
        f_sn  = st.text_input("Número de Serie (S/N)")
        f_est = st.selectbox("Estado Inicial", ["En proceso", "FINALIZADO"])
        f_com = st.text_area("Comentarios Iniciales")
        
        if st.form_submit_button("GUARDAR EN BASE DE DATOS"):
            if f_rma and f_emp:
                supabase.table("inventario_rma").insert({
                    "rma_number": f_rma, "n_ticket": f_ticket, "n_rq": f_rq,
                    "empresa": f_emp, "modelo": f_mod, "serial_number": f_sn, 
                    "informacion": f_est, "comentarios": f_com, "enviado": "NO"
                }).execute()
                st.success("✅ Guardado correctamente")
                st.rerun()
    
    if st.button("🚪 Salir del Sistema"):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 5. PANEL PRINCIPAL
st.title("📦 Control Central de Inventario")

try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['fecha_registro'] = pd.to_datetime(df['fecha_registro']).dt.date
        df['id_amigable'] = range(len(df), 0, -1)
        if st.session_state['rol'] == 'admin':
            df.insert(0, "Seleccionar", False)
except: df = pd.DataFrame()

if not df.empty:
    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Equipos Totales", len(df))
    c2.metric("En Reparación", len(df[df['informacion'] == 'En proceso']))
    c3.metric("Completados", len(df[df['informacion'] == 'FINALIZADO']))

    # Buscador y Exportación
    row1_1, row1_2 = st.columns([3, 1])
    with row1_1:
        busq = st.text_input("Filtro rápido", placeholder="🔍 Buscar por RMA, Cliente o Modelo...", label_visibility="collapsed")
    with row1_2:
        st.download_button("📥 Descargar Reporte (Excel)", preparar_excel(df), "RMA_Hikvision.xlsx", use_container_width=True)

    df_f = df[df.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)] if busq else df

    # --- 6. TABLA INTERACTIVA CON NOMBRES PROFESIONALES ---
    st.markdown("### 📋 Listado de Registros")
    
    es_admin = st.session_state['rol'] == 'admin'
    
    # Configuración de encabezados para humanos
    config_visual = {
        "id": None, # Oculto
        "Seleccionar": st.column_config.CheckboxColumn("Seleccionar"),
        "id_amigable": st.column_config.TextColumn("Nº", disabled=True),
        "fecha_registro": st.column_config.DateColumn("Fecha Registro", disabled=True),
        "rma_number": st.column_config.TextColumn("Número RMA"),
        "n_ticket": st.column_config.TextColumn("Ticket"),
        "n_rq": st.column_config.TextColumn("RQ"),
        "empresa": st.column_config.TextColumn("Empresa / Cliente"),
        "modelo": st.column_config.TextColumn("Modelo"),
        "serial_number": st.column_config.TextColumn("S/N"),
        "informacion": st.column_config.SelectboxColumn("Estado", options=["En proceso", "FINALIZADO"]),
        "enviado": st.column_config.SelectboxColumn("Enviado", options=["NO", "YES"]),
        "comentarios": st.column_config.TextColumn("Comentarios"),
        "fedex_number": st.column_config.TextColumn("Guía/Fedex")
    }

    df_editado = st.data_editor(
        df_f,
        column_config=config_visual,
        use_container_width=True,
        hide_index=True,
        disabled=not es_admin 
    )

    if es_admin:
        btn_col1, btn_col2, _ = st.columns([1.2, 1.2, 3])
        if btn_col1.button("💾 GUARDAR CAMBIOS EN TABLA"):
            for _, row in df_editado.iterrows():
                upd = {
                    "rma_number": row['rma_number'], "n_ticket": row['n_ticket'],
                    "informacion": row['informacion'], "enviado": row['enviado'],
                    "comentarios": row['comentarios'], "fedex_number": row['fedex_number']
                }
                supabase.table("inventario_rma").update(upd).eq("id", row['id']).execute()
            st.success("Base de datos actualizada")
            st.rerun()
        
        seleccionados = df_editado[df_editado.get('Seleccionar', False) == True]
        if not seleccionados.empty and btn_col2.button(f"🗑️ ELIMINAR ({len(seleccionados)})"):
            for id_db in seleccionados['id'].tolist():
                supabase.table("inventario_rma").delete().eq("id", id_db).execute()
            st.rerun()

    # --- 7. MODIFICACIÓN MANUAL (Para User o Admin por ID) ---
    st.markdown("---")
    with st.expander("🛠️ Edición Manual por Número de Registro (Nº)"):
        col_id, col_form = st.columns([1, 3])
        
        id_lista = sorted(df['id_amigable'].tolist(), reverse=True)
        id_sel = col_id.selectbox("Seleccione el Nº:", ["---"] + [str(i) for i in id_lista])
        
        if id_sel != "---":
            # Extraer fila por ID amigable
            item = df[df['id_amigable'] == int(id_sel)].iloc[0]
            
            with col_form.form("manual_edit"):
                st.markdown(f"**Editando Registro Nº {id_sel}**")
                m1, m2 = st.columns(2)
                m_rma = m1.text_input("RMA", value=item['rma_number'])
                m_tkt = m2.text_input("Ticket", value=str(item.get('n_ticket', '')))
                
                m3, m4 = st.columns(2)
                m_emp = m3.text_input("Empresa", value=item['empresa'])
                m_mod = m4.text_input("Modelo", value=item['modelo'])
                
                m_com = st.text_area("Comentarios", value=str(item.get('comentarios', '')))
                
                m5, m6 = st.columns(2)
                m_est = m5.selectbox("Estado", ["En proceso", "FINALIZADO"], 
                                   index=0 if item['informacion'] == "En proceso" else 1)
                m_env = m6.selectbox("¿Ya fue enviado?", ["NO", "YES"], 
                                   index=0 if item['enviado'] == "NO" else 1)

                if st.form_submit_button("ACTUALIZAR DATOS"):
                    upd_data = {
                        "rma_number": m_rma, "n_ticket": m_tkt, "empresa": m_emp,
                        "modelo": m_mod, "informacion": m_est, "enviado": m_env,
                        "comentarios": m_com
                    }
                    supabase.table("inventario_rma").update(upd_data).eq("id", item['id']).execute()
                    st.success(f"Nº {id_sel} actualizado.")
                    st.rerun()
else:
    st.info("No se encontraron registros en el sistema.")
