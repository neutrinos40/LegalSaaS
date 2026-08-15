from django.utils import timezone

from .models import Abonnement, UsageIA, TempsTravail


def _obtenir_abonnement(avocat):
    abo = getattr(avocat, 'abonnement', None)
    if abo is None:
        abo = Abonnement.objects.create(avocat=avocat)
    return abo


def quota_restant(avocat):
    abo = _obtenir_abonnement(avocat)
    if not abo.actif:
        return 0
    debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    utilise = UsageIA.objects.filter(avocat=avocat, date__gte=debut_mois).count()
    return max(abo.quota_mensuel - utilise, 0)


def enregistrer_usage(avocat, type_usage, octets=0):
    UsageIA.objects.create(avocat=avocat, type_usage=type_usage, octets=octets)


def demarrer_chrono(dossier, avocat):
    session = TempsTravail.objects.filter(dossier=dossier, avocat=avocat, fin__isnull=True).first()
    if session is None:
        session = TempsTravail.objects.create(dossier=dossier, avocat=avocat)
    return session


def arreter_chrono(dossier, avocat):
    session = TempsTravail.objects.filter(dossier=dossier, avocat=avocat, fin__isnull=True).first()
    if session is not None:
        session.fin = timezone.now()
        session.save()
    return session


def total_secondes_dossier(dossier):
    return sum(t.duree_secondes for t in TempsTravail.objects.filter(dossier=dossier))


def formater_secondes(secondes):
    heures, reste = divmod(int(secondes), 3600)
    minutes, secondes = divmod(reste, 60)
    return f"{heures}h {minutes:02d}m {secondes:02d}s"
