"""Email notification service - Single Responsibility: handles all outbound emails."""
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app


def _send_email_async(app, to_email, subject, html_body):
    """Send email in a background thread so requests aren't blocked."""
    with app.app_context():
        try:
            cfg = app.config
            msg = MIMEMultipart('alternative')
            msg['From'] = cfg['MAIL_FROM']
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(html_body, 'html'))

            with smtplib.SMTP(cfg['MAIL_SERVER'], cfg['MAIL_PORT']) as server:
                if cfg.get('MAIL_USE_TLS'):
                    server.starttls()
                server.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
                server.sendmail(cfg['MAIL_USERNAME'], to_email, msg.as_string())
            print(f"[EMAIL] Sent to {to_email}: {subject}")
        except Exception as e:
            print(f"[EMAIL ERROR] {e}")


def send_email(to_email, subject, html_body):
    """Queue an email to be sent asynchronously. No-op if MAIL_ENABLED is False."""
    app = current_app._get_current_object()
    if not app.config.get('MAIL_ENABLED'):
        print(f"[EMAIL DISABLED] Would send to {to_email}: {subject}")
        return

    thread = threading.Thread(
        target=_send_email_async,
        args=(app, to_email, subject, html_body)
    )
    thread.daemon = True
    thread.start()


def notify_comment_email(owner_email, owner_name, commenter_name, project_title, comment_text):
    """Send an email notification when someone comments on a project."""
    subject = f"💬 New comment on \"{project_title}\" — MzansiBuilds"
    html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px;">
        <div style="background:#16a34a;color:#fff;padding:16px 24px;border-radius:8px 8px 0 0;">
            <h2 style="margin:0;">MzansiBuilds</h2>
        </div>
        <div style="background:#fff;border:1px solid #e5e7eb;border-top:none;padding:24px;border-radius:0 0 8px 8px;">
            <p>Hi <strong>{owner_name}</strong>,</p>
            <p><strong>{commenter_name}</strong> commented on your project <strong>"{project_title}"</strong>:</p>
            <blockquote style="border-left:3px solid #16a34a;padding:8px 16px;margin:16px 0;background:#f0fdf4;border-radius:4px;color:#333;">
                {comment_text}
            </blockquote>
            <p style="color:#6b7280;font-size:0.85rem;margin-top:24px;">— MzansiBuilds Team</p>
        </div>
    </div>
    """
    send_email(owner_email, subject, html)


def notify_collab_email(owner_email, owner_name, requester_name, project_title, message):
    """Send an email notification when someone requests to collaborate."""
    subject = f"🤝 Collaboration request on \"{project_title}\" — MzansiBuilds"
    msg_block = f"""
            <blockquote style="border-left:3px solid #16a34a;padding:8px 16px;margin:16px 0;background:#f0fdf4;border-radius:4px;color:#333;">
                {message}
            </blockquote>
    """ if message else ""
    html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px;">
        <div style="background:#16a34a;color:#fff;padding:16px 24px;border-radius:8px 8px 0 0;">
            <h2 style="margin:0;">MzansiBuilds</h2>
        </div>
        <div style="background:#fff;border:1px solid #e5e7eb;border-top:none;padding:24px;border-radius:0 0 8px 8px;">
            <p>Hi <strong>{owner_name}</strong>,</p>
            <p><strong>{requester_name}</strong> wants to collaborate on your project <strong>"{project_title}"</strong>!</p>
            {msg_block}
            <p>Log in to MzansiBuilds to accept or decline this request.</p>
            <p style="color:#6b7280;font-size:0.85rem;margin-top:24px;">— MzansiBuilds Team</p>
        </div>
    </div>
    """
    send_email(owner_email, subject, html)
