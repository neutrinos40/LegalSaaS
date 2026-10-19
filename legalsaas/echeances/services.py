import re

from django.conf import settings
from twilio.rest import Client


def normaliser_telephone(numero):
    """Transforme 06 12 34 56 78 ou 14183212633 en +331... / +1418... (format Twilio)."""
    numero = re.sub(r'[\s.\-()]', '', numero or '')
    if not numero.startswith('+'):
        if numero.startswith('0') and len(numero) == 10:      # 06... → +33...
            numero = '+33' + numero[1:]
        else:
            numero = '+' + numero                               # 1418... → +1418...
    return numero


def envoyer_sms(numero, modele='sms_appointment_reminders'):
    """Envoie un SMS via Twilio. Compte trial = body doit être un modèle prédéfini.
    Modèles valides : sms_2fa, sms_appointment_reminders, sms_order_confirmation,
    sms_delivery_updates, sms_customer_support, sms_marketing_promotions,
    sms_event_notifications, sms_account_alerts, sms_feedback_surveys, sms_internal_alerts."""
    numero = normaliser_telephone(numero)
    if not numero:
        raise ValueError("Numéro de téléphone manquant")

    client_twilio = Client(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN,
    )

    message_twilio = client_twilio.messages.create(
        body=modele,
        from_=settings.TWILIO_PHONE_NUMBER,
        to=numero,
    )
    return message_twilio.sid