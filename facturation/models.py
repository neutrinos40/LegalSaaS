from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from dossiers.models import Dossier
from clients.models import Client


class Abonnement(models.Model):
    avocat = models.OneToOneField(User, on_delete=models.CASCADE, related_name='abonnement')
    nom_plan = models.CharField(max_length=50, default='Standard', verbose_name=_("Plan"))
    prix_mensuel = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                       verbose_name=_("Prix mensuel ($)"))
    quota_mensuel = models.PositiveIntegerField(default=50, verbose_name=_("Quota mensuel (appels IA)"))
    actif = models.BooleanField(default=True, verbose_name=_("Actif"))
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))

    def __str__(self):
        return f"{self.avocat.username} — {self.nom_plan}"


class UsageIA(models.Model):
    TYPE_USAGE_CHOICES = [
        ('generation', _('Génération')),
        ('analyse', _('Analyse')),
    ]

    avocat = models.ForeignKey(User, on_delete=models.CASCADE, related_name='usages_ia')
    type_usage = models.CharField(max_length=20, choices=TYPE_USAGE_CHOICES, verbose_name=_("Type"))
    octets = models.PositiveIntegerField(default=0, verbose_name=_("Taille (octets)"))
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("Date"))

    def __str__(self):
        return f"{self.avocat.username} — {self.get_type_usage_display()}"


class Facture(models.Model):
    STATUT_CHOICES = [
        ('brouillon', _('Brouillon')),
        ('envoyee', _('Envoyée')),
        ('payee', _('Payée')),
    ]

    avocat = models.ForeignKey(User, on_delete=models.CASCADE, related_name='factures')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='factures')
    dossier = models.ForeignKey(Dossier, on_delete=models.SET_NULL, null=True, blank=True, related_name='factures')
    mois = models.CharField(max_length=7, verbose_name=_("Mois (AAAA-MM)"))
    montant = models.DecimalField(max_digits=8, decimal_places=2, verbose_name=_("Montant ($)"))
    payee = models.BooleanField(default=False, verbose_name=_("Payée"))
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon', verbose_name=_("Statut"))
    date_emission = models.DateTimeField(auto_now_add=True, verbose_name=_("Date d'émission"))

    class Meta:
        unique_together = ('avocat', 'client', 'mois')

    def __str__(self):
        return f"{self.avocat.username} — {self.mois} — {self.montant}"


class TempsTravail(models.Model):
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name='temps_travail')
    avocat = models.ForeignKey(User, on_delete=models.CASCADE, related_name='temps_travail')
    debut = models.DateTimeField(default=timezone.now, verbose_name=_("Début"))
    fin = models.DateTimeField(null=True, blank=True, verbose_name=_("Fin"))
    description = models.CharField(max_length=255, blank=True, default='', verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Temps de travail")
        verbose_name_plural = _("Temps de travail")
        ordering = ['-debut']

    def __str__(self):
        return f"{self.avocat.username} — {self.dossier.titre} — {self.duree}"

    @property
    def en_cours(self):
        return self.fin is None

    @property
    def duree_secondes(self):
        fin = self.fin or timezone.now()
        return max(int((fin - self.debut).total_seconds()), 0)

    @property
    def duree(self):
        s = self.duree_secondes
        heures, reste = divmod(s, 3600)
        minutes, secondes = divmod(reste, 60)
        return f"{heures}h {minutes:02d}m {secondes:02d}s"


class EntreeTemps(models.Model):
    CATEGORIE_ACTIVITE_CHOICES = [
        ('redaction', _('Rédaction')),
        ('recherche', _('Recherche')),
        ('rencontre', _('Rencontre client')),
        ('procedure', _('Procédure')),
        ('autre', _('Autre')),
    ]

    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name='entrees_temps')
    avocat = models.ForeignKey(User, on_delete=models.CASCADE, related_name='entrees_temps')
    date = models.DateField(default=timezone.localdate, verbose_name=_("Date"))
    duree_minutes = models.PositiveIntegerField(verbose_name=_("Durée (minutes)"))
    description = models.TextField(blank=True, default='', verbose_name=_("Description"))
    categorie_activite = models.CharField(max_length=20, choices=CATEGORIE_ACTIVITE_CHOICES,
                                          default='redaction', verbose_name=_("Catégorie d'activité"))
    taux_horaire_applique = models.DecimalField(max_digits=7, decimal_places=2,
                                                verbose_name=_("Taux horaire appliqué ($)"))
    montant = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                  verbose_name=_("Montant ($)"))
    non_facturable = models.BooleanField(default=False, verbose_name=_("Non facturable"))
    saisie_manuelle = models.BooleanField(default=False, verbose_name=_("Saisie manuelle"))
    cree_le = models.DateTimeField(auto_now_add=True, verbose_name=_("Créé le"))

    class Meta:
        verbose_name = _("Entrée de temps")
        verbose_name_plural = _("Entrées de temps")
        ordering = ['-date', '-cree_le']

    def save(self, *args, **kwargs):
        self.montant = (self.taux_horaire_applique * self.duree_minutes / Decimal(60)).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)

    @property
    def duree_formatee(self):
        heures, minutes = divmod(self.duree_minutes, 60)
        return f"{heures}h {minutes:02d}min"

    def __str__(self):
        return f"{self.avocat.username} — {self.dossier.titre} — {self.duree_formatee}"
