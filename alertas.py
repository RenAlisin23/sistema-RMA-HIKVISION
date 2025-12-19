import pandas as pd
from datetime import datetime, timezone
from supabase import create_client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# 1. CARGA DE VARIABLES DESDE GITHUB SECRETS
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
EMAIL_USER = os.environ.get("GMAIL_USER") 
EMAIL_PASS = os.environ.get("GMAIL_PASS") 

def enviar_alertas():
    # Validación de seguridad
    if not all([URL, KEY, EMAIL_USER, EMAIL_PASS]):
        print("❌ Error: Faltan Secrets en GitHub (GMAIL_USER o GMAIL_PASS).")
        return

    supabase = create_client(URL, KEY)
    
    # 2. OBTENER DESTINATARIOS (No importa si son Outlook, Gmail o Corporativos)
    res_contactos = supabase.table("lista_contactos").select("email").execute()
    destinatarios = [c['email'] for c in res_contactos.data if c.get('email')]
    
    if not destinatarios:
        print("No hay destinatarios en la tabla lista_contactos.")
        return

    # 3. OBTENER EQUIPOS PENDIENTES
    res_rma = supabase.table("inventario_rma").select("*").neq("enviado", "YES").execute()
    df = pd.DataFrame(res_rma.data)

    if df.empty:
        print("No hay equipos pendientes de envío.")
        return

    # 4. FILTRAR EQUIPOS CON +30 DÍAS
    df['fecha_registro'] = pd.to_datetime(df['fecha_registro'], utc=True)
    hoy = datetime.now(timezone.utc)
    df['dias_en_taller'] = (hoy - df['fecha_registro']).dt.days
    vencidos = df[df['dias_en_taller'] >= 30]

    if not vencidos.empty:
        # Diseño de la tabla para el correo
        filas_html = ""
        for _, fila in vencidos.iterrows():
            filas_html += f"""
                <tr>
                    <td style='padding:10px; border:1px solid #ddd;'>{fila['rma_number']}</td>
                    <td style='padding:10px; border:1px solid #ddd;'>{fila['empresa']}</td>
                    <td style='padding:10px; border:1px solid #ddd; color:#d9534f;'><b>{fila['dias_en_taller']} días</b></td>
                </tr>
            """

        # 5. CONFIGURACIÓN DEL MENSAJE (Cuerpo del correo)
        msg = MIMEMultipart()
        msg['From'] = f"Sistema Alertas RMA <{EMAIL_USER}>"
        msg['To'] = ", ".join(destinatarios)
        msg['Subject'] = f"URGENTE: {len(vencidos)} RMAs excedieron los 30 días"

        html_final = f"""
        <html>
            <body style='font-family: Arial, sans-serif;'>
                <h2 style='color: #d9534f;'>Reporte de Equipos con Retraso Crítico</h2>
                <p>Los siguientes equipos llevan más de 30 días registrados sin ser enviados:</p>
                <table style='width:100%; border-collapse: collapse;'>
                    <tr style='background-color: #f8f9fa;'>
                        <th style='padding:10px; border:1px solid #ddd;'>Número RMA</th>
                        <th style='padding:10px; border:1px solid #ddd;'>Empresa</th>
                        <th style='padding:10px; border:1px solid #ddd;'>Días transcurridos</th>
                    </tr>
                    {filas_html}
                </table>
                <p style='margin-top:20px; font-size: 12px; color: #777;'>
                    Este es un correo automático generado por el sistema de inventario.
                </p>
            </body>
        </html>
        """
        msg.attach(MIMEText(html_final, 'html'))

        # 6. ENVÍO 
        try:
            # Usamos el puerto 465 (SSL) 
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(EMAIL_USER, EMAIL_PASS)
                server.sendmail(EMAIL_USER, destinatarios, msg.as_string())
            print(f"Alertas enviadas correctamente a {len(destinatarios)} destinatarios.")
        except Exception as e:
            print(f"❌ Error al conectar con Gmail: {e}")

if __name__ == "__main__":
    enviar_alertas()
