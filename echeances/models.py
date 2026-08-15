from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from clients.models import Client
from dossiers.models import Dossier


class Echeance(models.Model):
    STATUT_CHOICES = [
        ('a_venir', _('À venir')),
        ('respecte', _('Respecté')),
        ('depasse', _('Dépassé')),
    ]
       ### Alerte email 
    alerte_envoyee = models.BooleanField(default=False)
    date_alerte_envoyee = models.DateTimeField(blank=True, null=True)
                 
       
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name='echeances')
    type_delai = models.CharField(max_length=100)
    date_limite = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='a_venir')
    description = models.TextField(blank=True, default='', verbose_name=_("Description"))
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type_delai} - {self.dossier} - {self.date_limite}"


class RendezVous(models.Model):
    MODE_CHOICES = [
        ('presentiel', _('Présentiel')),
        ('visio', _('Visioconférence')),
        ('telephone', _('Téléphone')),
    ]
    STATUT_CHOICES = [
        ('planifie', _('Planifié')),
        ('complete', _('Complété')),
        ('annule', _('Annulé')),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='rendez_vous')
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name='rendez_vous', blank=True, null=True)
    avocat = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rendez_vous')
    date_heure = models.DateTimeField()
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='presentiel')
    lieu_ou_lien = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='planifie')

    def __str__(self):
        return f"RDV — {self.client} — {self.date_heure.strftime('%d/%m/%Y %H:%M')}"
        
        
        ##### echa
 