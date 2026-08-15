from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Client(models.Model):
    TYPE_CLIENT_CHOICES = [
        ('individu', _('Individu')),
        ('compagnie', _('Compagnie')),
    ]

    type_client = models.CharField(max_length=20, choices=TYPE_CLIENT_CHOICES,
                                   default='individu', verbose_name=_("Type de client"))

    nom = models.CharField(max_length=100, blank=True, default='', verbose_name=_("Nom"))
    prenom = models.CharField(max_length=100, blank=True, default='', verbose_name=_("Prénom"))
    raison_sociale = models.CharField(max_length=200, blank=True, default='',
                                      verbose_name=_("Raison sociale"))
    numero_entreprise = models.CharField(max_length=30, blank=True, default='',
                                         verbose_name=_("Numéro d'entreprise (NEQ)"))
    nom_representant = models.CharField(max_length=200, blank=True, default='',
                                        verbose_name=_("Nom du représentant"))
    email = models.EmailField(blank=True, null=True, verbose_name=_("Courriel"))
    telephone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("Téléphone"))
    adresse = models.TextField(blank=True, default='', verbose_name=_("Adresse"))

    avocat = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='clients', verbose_name=_("Avocat"))
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))

    @property
    def nom_complet(self):
        if self.type_client == 'compagnie':
            return self.raison_sociale or self.nom_representant or "—"
        return f"{self.prenom} {self.nom}".strip() or "—"

    def __str__(self):
        return self.nom_complet
