import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

def send_reset_email(to_email: str, display_name: str, reset_link: str) -> bool:
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print("\n[WARNING] SMTP credentials are not defined in .env file!")
        print(f"Skipping SMTP transmission for {to_email}. Reset link: {reset_link}\n")
        return False

    # Create message container
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Reset Your Aivan ERP Password"
    msg['From'] = settings.SMTP_FROM or settings.SMTP_USER
    msg['To'] = to_email

    # Premium responsive HTML email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reset Your Password</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: #f8fafc;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
            }}
            .email-container {{
                max-width: 600px;
                margin: 40px auto;
                background-color: #ffffff;
                border-radius: 24px;
                padding: 40px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                border: 1px solid #e2e8f0;
            }}
            .logo-header {{
                text-align: center;
                margin-bottom: 35px;
            }}
            .logo-img {{
                width: 130px;
                height: auto;
            }}
            .company-name {{
                font-size: 20px;
                font-weight: 800;
                color: #1e293b;
                margin: 12px 0 0;
                letter-spacing: -0.5px;
            }}
            .title {{
                font-size: 22px;
                font-weight: 800;
                color: #0f172a;
                margin-bottom: 20px;
                text-align: center;
                letter-spacing: -0.5px;
            }}
            .content {{
                font-size: 15px;
                line-height: 1.6;
                color: #475569;
                margin-bottom: 24px;
            }}
            .btn-container {{
                text-align: center;
                margin: 35px 0;
            }}
            .btn {{
                background: linear-gradient(90deg, #e11d48 0%, #4c1d95 100%);
                color: #ffffff !important;
                padding: 16px 36px;
                text-decoration: none;
                border-radius: 16px;
                font-weight: 700;
                font-size: 16px;
                display: inline-block;
                box-shadow: 0 10px 20px -5px rgba(225, 29, 72, 0.3);
            }}
            .divider {{
                height: 1px;
                background-color: #f1f5f9;
                margin: 30px 0;
            }}
            .warning {{
                font-size: 13px;
                color: #94a3b8;
                line-height: 1.5;
            }}
            .footer {{
                text-align: center;
                font-size: 12px;
                color: #94a3b8;
                margin-top: 40px;
                line-height: 1.5;
            }}
        </style>
    </head>
    <body>
        <div style="background-color: #f8fafc; padding: 20px 0; width: 100%;">
            <div class="email-container">
                <div class="logo-header">
                    <img src="https://aivan360.com/NewTheme/assets/img/AivanLogo.png" alt="AIVAN Logo" class="logo-img" />
                    <h1 class="company-name">AIVAN ERP</h1>
                </div>
                
                <h2 class="title">Password Recovery Request</h2>
                
                <p class="content">Hello <strong>{display_name}</strong>,</p>
                <p class="content">We received a request to reset the password associated with your Aivan ERP account. To proceed, please click the secure recovery button below:</p>
                
                <div class="btn-container">
                    <a href="{reset_link}" class="btn" target="_blank">Reset Password Now</a>
                </div>
                
                <p class="content">If you are having trouble with the button, copy and paste the following URL directly into your web browser's address bar:</p>
                <p class="content" style="word-break: break-all; font-size: 13px; background-color: #f8fafc; padding: 14px; border-radius: 12px; border: 1px solid #e2e8f0; font-family: monospace; color: #64748b;">
                    {reset_link}
                </p>
                
                <div class="divider"></div>
                
                <p class="warning">
                    <strong>Note:</strong> This password reset link is highly secure and will expire in 15 minutes. If you did not make this request, you can safely ignore this email; your current password will remain safe and unaltered.
                </p>
            </div>
            
            <div class="footer">
                &copy; 2026 Aivan 360 Solutions. All rights reserved.<br>
                This is a secure, system-generated notification. Please do not reply.
            </div>
        </div>
    </body>
    </html>
    """

    part = MIMEText(html_content, 'html')
    msg.attach(part)

    try:
        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
            
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM or settings.SMTP_USER, to_email, msg.as_string())
        server.quit()
        print(f"[SUCCESS] Real password reset email dispatched successfully to {to_email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send SMTP email to {to_email}: {str(e)}")
        return False
