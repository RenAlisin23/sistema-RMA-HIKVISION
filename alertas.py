import pandas as pd
from datetime import datetime, timezone
from supabase import create_client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# Configuración (GitHub recogerá estos nombres del YAML)
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
EMAIL_USER = os.environ.get("GMAIL_USER") 
EMAIL_PASS = os.environ.get("GMAIL_PASS") 

def enviar_alertas():
    if not all([URL, KEY, EMAIL_USER, EMAIL_PASS]):
        print("❌ Error: Faltan variables de configuración.")
        return

    supabase = create_client(URL, KEY)
    
    # 1. Obtener destinatarios desde Supabase
    res_contactos = supabase.table("lista_contactos").select("email").execute()
    destinatarios = [c['email'] for c in res_contactos.data if c.get('email')]
    
    if not destinatarios:
        print("No hay destinatarios.")
        return

    # 2. Obtener equipos +30 días
    res_rma = supabase.table("inventario_rma").select("*").neq("enviado", "YES").execute()
    df = pd.DataFrame(res_rma.data)

    if df.empty:
        print("Nada pendiente.")
        return

    df['fecha_registro'] = pd.to_datetime(df['fecha_registro'], utc=True)
    vencidos = df[(datetime.now(timezone.utc) - df['fecha_registro']).dt.days >= 30]

    if not vencidos.empty:
        # Estructura del correo
        filas_html = "".join([f"<tr><td style='border:1px solid #444; padding:8px;'>{r['rma_number']}</td><td style='border:1px solid #444; padding:8px;'>{r['empresa']}</td><td style='border:1px solid #444; padding:8px; color:red;'>{(datetime.now(timezone.utc) - pd.to_datetime(r['fecha_registro'], utc=True)).days} días</td></tr>" for _, r in vencidos.iterrows()])

        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = ", ".join(destinatarios)
        msg['Subject'] = f"ALERTA: {len(vencidos)} RMAs con retraso"

        cuerpo = f"<h2>Equipos con más de 30 días</h2><table style='width:100%; border-collapse:collapse;'>{filas_html}</table>"
        msg.attach(MIMEText(cuerpo, 'html'))

        # ENVÍO POR GMAIL (Puerto 465 SSL)
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(EMAIL_USER, EMAIL_PASS)
                server.sendmail(EMAIL_USER, destinatarios, msg.as_string())
            print(f"Alerta enviada con éxito vía Gmail a {len(destinatarios)} correos.")
        except Exception as e:
            print(f"❌ Error en Gmail: {e}")

if __name__ == "__main__":
    enviar_alertas()
