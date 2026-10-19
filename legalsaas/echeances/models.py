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
        # Traçabilité du calcul automatique (vide si saisie manuelle)
    calcul_automatique = models.BooleanField(default=False, verbose_name=_("Calculé automatiquement"))
    date_depart = models.DateField(null=True, blank=True, verbose_name=_("Date de départ du délai"))
    reference_legale = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Référence légale"))
    duree_delai = models.CharField(max_length=100, blank=True, default='', verbose_name=_("Durée appliquée"))
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


class Tache(models.Model):
    PRIORITE_CHOICES = [
        ('basse', _('Basse')),
        ('normale', _('Normale')),
        ('haute', _('Haute')),
    ]

    titre = models.CharField(max_length=200, verbose_name=_("Titre"))
    description = models.TextField(blank=True, default='', verbose_name=_("Description"))
    date_echeance = models.DateField(null=True, blank=True, verbose_name=_("Date d'échéance"))
    priorite = models.CharField(max_length=10, choices=PRIORITE_CHOICES, default='normale')
    terminee = models.BooleanField(default=False, verbose_name=_("Terminée"))
    avocat = models.ForeignKey(User, on_delete=models.CASCADE, related_name='taches')
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name='taches',
                                blank=True, null=True)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, related_name='taches',
                               blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Tâche")
        verbose_name_plural = _("Tâches")
        ordering = ['terminee', 'date_echeance', '-date_creation']

    def __str__(self):
        return self.titre