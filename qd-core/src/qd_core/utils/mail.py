import smtplib
from email.mime.text import MIMEText
from urllib import parse as urllib_parse

from tornado import httpclient

from qd_core.config import get_settings
from qd_core.filters.convert import to_bytes
from qd_core.utils.decorator import log_and_raise_error
from qd_core.utils.i18n import gettext
from qd_core.utils.log import Log

logger_mail = Log("QD.Core.Utils").getlogger()


@log_and_raise_error(logger_mail, "Send mail error: %s")
async def send_mail(to, subject, text=None, html=None, shark=False):
    if not get_settings().mail.mailgun_key:
        subtype = "html" if html else "plain"
        await _send_mail_by_smtp(to, subject, html or text or "", subtype)
        return

    return _send_mail_by_mailgun(to, subject, text, html, shark)


async def _send_mail_by_smtp(to, subject, text=None, subtype="html"):
    if not get_settings().mail.mail_smtp:
        logger_mail.warning("no smtp")
        return
    msg = MIMEText(text, _subtype=subtype, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = get_settings().mail.mail_from
    msg["To"] = to

    logger_mail.info(gettext("send mail to %s", to))
    tls_established = False

    # Create SMTP connection according to the configuration
    if get_settings().mail.mail_starttls:  # use starttls
        s = smtplib.SMTP(get_settings().mail.mail_smtp, get_settings().mail.mail_port or 587)
        try:
            s.starttls()
            tls_established = True
        except smtplib.SMTPException as e:
            logger_mail.error(gettext("smtp starttls failed: %s"), e, exc_info=get_settings().log.traceback_print)
    if not tls_established:
        if get_settings().mail.mail_ssl:
            s = smtplib.SMTP_SSL(get_settings().mail.mail_smtp, get_settings().mail.mail_port or 465)
        else:
            s = smtplib.SMTP(get_settings().mail.mail_smtp, get_settings().mail.mail_port or 25)

    try:
        # Only attempt login if user and password are set
        if get_settings().mail.mail_user and get_settings().mail.mail_password:
            s.login(get_settings().mail.mail_user, get_settings().mail.mail_password)
        s.sendmail(get_settings().mail.mail_from, to, msg.as_string())
    except smtplib.SMTPException as e:
        logger_mail.error(gettext("smtp sendmail error: %s"), e, exc_info=get_settings().log.traceback_print)
    finally:
        # If sending fails, still close the connection
        s.quit()


async def _send_mail_by_mailgun(to, subject, text=None, html=None, shark=False):
    httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
    if shark:
        client = httpclient.AsyncHTTPClient()
    else:
        client = httpclient.HTTPClient()

    body = {
        "from": to_bytes(
            gettext("QD Notification <noreply@{mailgun_domain}>").format(
                mailgun_domain=get_settings().mail.mailgun_domain
            )
        ),
        "to": to_bytes(to),
        "subject": to_bytes(subject),
    }

    if text:
        body["text"] = to_bytes(text)
    elif html:
        body["html"] = to_bytes(html)
    else:
        raise Exception(gettext("need text or html"))

    req = httpclient.HTTPRequest(
        method="POST",
        url=f"https://api.mailgun.net/v3/{get_settings().mail.mailgun_domain}/messages",
        auth_username="api",
        auth_password=get_settings().mail.mailgun_key,
        body=urllib_parse.urlencode(body),
    )
    res = await client.fetch(req)
    return res
