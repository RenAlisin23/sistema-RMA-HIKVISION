import pandas as pd
from datetime import datetime, timezone
from supabase import create_client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# Configuración de variables (GitHub Actions)
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
EMAIL_USER = os.environ.get("OUTLOOK_USER") 
EMAIL_PASS = os.environ.get("OUTLOOK_PASS") 

def enviar_alertas():
    # Validación de credenciales
    if not all([URL, KEY, EMAIL_USER, EMAIL_PASS]):
        print("Error: Faltan variables de configuración en GitHub.")
        return

    supabase = create_client(URL, KEY)
    
    # 1. Obtener TODOS los destinatarios de la tabla
    try:
        res_contactos = supabase.table("lista_contactos").select("email").execute()
        # Creamos una lista limpia de correos: ['user1@mail.com', 'user2@mail.com', ...]
        destinatarios = [c['email'] for c in res_contactos.data if c.get('email')]
    except Exception as e:
        print(f"Error al leer contactos: {e}")
        return
    
    if not destinatarios:
        print("No hay correos registrados en 'lista_contactos'.")
        return

    # 2. Obtener equipos que NO han sido marcados como 'YES' (enviados)
    res_rma = supabase.table("inventario_rma").select("*").neq("enviado", "YES").execute()
    df = pd.DataFrame(res_rma.data)

    if df.empty:
        print("Todo al día: No hay equipos pendientes de envío.")
        return

    # 3. Filtrar los que llevan más de 30 días
    df['fecha_registro'] = pd.to_datetime(df['fecha_registro'], utc=True)
    hoy = datetime.now(timezone.utc)
    df['dias_HQ'] = (hoy - df['fecha_registro']).dt.days
    vencidos = df[df['dias_HQ'] >= 30]

    if not vencidos.empty:
        # Construcción de la tabla HTML
        filas_html = ""
        for _, fila in vencidos.iterrows():
            filas_html += f"""
                <tr>
                    <td style='padding:10px; border:1px solid #444;'>{fila['rma_number']}</td>
                    <td style='padding:10px; border:1px solid #444;'>{fila['empresa']}</td>
                    <td style='padding:10px; border:1px solid #444; color:red;'><b>{fila['dias_HQ']} días</b></td>
                </tr>
            """

        # --- PREPARACIÓN DEL CORREO ---
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        # Ponemos todos los correos separados por coma
        msg['To'] = ", ".join(destinatarios)
        msg['Subject'] = f"REPORTE CRÍTICO: {len(vencidos)} Equipos con Retraso (+30 días)"

        cuerpo_html = f"""
            <div style='background-color:#f4f4f4; color:#333; padding:20px; font-family:sans-serif;'>
                <h2 style='color:#eb1c24;'>Alerta de Equipos Estancados en Taller</h2>
                <p>Estimados, los siguientes registros han superado el límite de 30 días:</p>
                <table style='border-collapse:collapse; width:100%; background:#fff;'>
                    <tr style='background:#eb1c24; color:#fff;'>
                        <th style='padding:10px; border:1px solid #444;'>Número RMA</th>
                        <th style='padding:10px; border:1px solid #444;'>Empresa</th>
                        <th style='padding:10px; border:1px solid #444;'>Tiempo Transcurrido</th>
                    </tr>
                    {filas_html}
                </table>
                <p style='font-size:12px; color:#777; margin-top:20px;'>
                    Este es un recordatorio automático. Para dejar de recibir alertas de estos equipos, márquelos como 'YES' en el panel de control.
                </p>
            </div>
        """
        msg.attach(MIMEText(cuerpo_html, 'html'))

        # --- ENVÍO POR OUTLOOK ---
        try:
            server = smtplib.SMTP('smtp.office365.com', 587)
            server.starttls() 
            server.login(EMAIL_USER, EMAIL_PASS)
            # Enviamos a la lista completa
            server.sendmail(EMAIL_USER, destinatarios, msg.as_string())
            server.quit()
            print(f"🚀 ÉXITO: Alerta enviada a {len(destinatarios)} personas.")
        except Exception as e:
            print(f"❌ Falló el servidor de Outlook: {e}")

if __name__ == "__main__":
    enviar_alertas()
