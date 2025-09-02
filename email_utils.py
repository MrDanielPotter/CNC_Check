
import smtplib, ssl, os, json, mimetypes
from email.message import EmailMessage
from typing import Dict, Any

def send_email_with_attachment(settings: dict, subject: str, body: str, file_path: str) -> str:
    host = settings.get("smtp_host")
    port = int(settings.get("smtp_port") or 0)
    user = settings.get("smtp_user")
    password = settings.get("smtp_pass")
    use_ssl = settings.get("smtp_ssl") == "1"
    use_tls = settings.get("smtp_tls") == "1"
    recipients = [r.strip() for r in (settings.get("recipients") or "").split(",") if r.strip()]

    if not (host and port and user and password and recipients):
        raise RuntimeError("SMTP settings incomplete")

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    with open(file_path, "rb") as f:
        data = f.read()
    fname = os.path.basename(file_path)
    
    # Determine MIME type based on file extension
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        maintype, subtype = mime_type.split('/', 1)
    else:
        # Default to PDF if type cannot be determined
        maintype, subtype = "application", "pdf"
    
    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=fname)

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context()) as s:
            s.login(user, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as s:
            if use_tls:
                s.starttls(context=ssl.create_default_context())
            s.login(user, password)
            s.send_message(msg)
    return "OK"
