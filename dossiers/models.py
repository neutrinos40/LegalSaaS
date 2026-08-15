from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from clients.models import Client


class Dossier(models.Model):
    TYPE_PROCEDURE_CHOICES = [
        ('appel_civil', _('Appel civil')),
        ('contestation', _('Contestation')),
        ('requete_introductive', _('Requête introductive')),
    ]

    STATUT_CHOICES = [
        ('actif', _('Actif')),
        ('ferme', _('Fermé')),
        ('suspendu', _('Suspendu')),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='dossiers')
    avocat = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dossiers')
    titre = models.CharField(max_length=200)
    type_procedure = models.CharField(max_length=50, choices=TYPE_PROCEDURE_CHOICES)
    date_debut = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='actif')
    notes = models.TextField(blank=True, null=True)
    taux_horaire = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True,
                                       verbose_name=_("Taux horaire du dossier ($)"))

    def __str__(self):
        return f"{self.titre} - {self.client}"


class ProfilAvocat(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil')
    telephone = models.CharField(max_length=20, blank=True, null=True)
    taux_horaire_defaut = models.DecimalField(max_digits=7, decimal_places=2, default=0,
                                              verbose_name=_("Taux horaire par défaut ($)"))
    seuil_rouge = models.PositiveIntegerField(default=2)
    seuil_orange = models.PositiveIntegerField(default=7)

    def __str__(self):
        return f"Profil de {self.user.username}"


class Communication(models.Model):
    TYPE_COMMUNICATION_CHOICES = [
        ('courriel', _('Courriel')),
        ('appel', _('Appel téléphonique')),
        ('lettre', _('Lettre')),
        ('autre', _('Autre')),
    ]

    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name='communications')
    avocat = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='communications', verbose_name=_("Avocat"))
    type_communication = models.CharField(max_length=20, choices=TYPE_COMMUNICATION_CHOICES,
                                          default='courriel', verbose_name=_("Type"))
    date = models.DateTimeField(default=timezone.now, verbose_name=_("Date"))
    description = models.TextField(verbose_name=_("Description"))

    def __str__(self):
        return f"{self.get_type_communication_display()} — {self.dossier.titre}"