from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from echeances.models import Echeance
from echeances.services import envoyer_sms


class Command(BaseCommand):
    help = "Vérifie les échéances à venir et envoie une alerte email + SMS si nécessaire"

    def handle(self, *args, **options):
        dans_7_jours = timezone.now().date() + timedelta(days=7)

        echeances_a_risque = Echeance.objects.filter(
            date_limite=dans_7_jours,
            statut='a_venir',
            alerte_envoyee=False,
        )

        for echeance in echeances_a_risque:
            avocat = echeance.dossier.avocat
            dossier = echeance.dossier
            client = dossier.client
            succes = False

            # ---- EMAIL à l'avocat ----
            if avocat.email:
                try:
                    send_mail(
                        subject=f"Échéance dans 7 jours — {dossier.titre}",
                        message=(
                            f"Bonjour {avocat.get_full_name() or avocat.username},\n\n"
                            f"L'échéance suivante arrive à terme le {echeance.date_limite} :\n"
                            f"Dossier : {dossier.titre}\n"
                            f"Type de délai : {echeance.type_delai}\n\n"
                            f"Veuillez agir en conséquence."
                        ),
                        from_email=None,
                        recipient_list=[avocat.email],
                    )
                    succes = True
                    self.stdout.write(self.style.SUCCESS(
                        f"Email envoyé pour {echeance} à {avocat.email}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Échec email pour {echeance} : {e}"))

            # ---- SMS au client ----
            if client.telephone:
                try:
                    envoyer_sms(
                        numero=client.telephone,
                        modele='sms_appointment_reminders',
                    )
                    succes = True
                    self.stdout.write(self.style.SUCCESS(
                        f"SMS envoyé pour {echeance} à {client.telephone}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Échec SMS pour {echeance} : {e}"))

            if succes:
                echeance.alerte_envoyee = True
                echeance.date_alerte_envoyee = timezone.now()
                echeance.save()
