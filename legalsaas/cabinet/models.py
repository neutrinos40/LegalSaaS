from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Cabinet(models.Model):
    nom = models.CharField(max_length=200, verbose_name=_("Nom du cabinet"))
    chef = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='cabinet_chef', verbose_name=_("Chef de cabinet"))
    logo = models.ImageField(upload_to='cabinet_logos/', blank=True, null=True,
                             verbose_name=_("Logo"))
    adresse = models.CharField(max_length=300, blank=True, default='',
                               verbose_name=_("Adresse"))
    telephone = models.CharField(max_length=30, blank=True, default='',
                                 verbose_name=_("Téléphone"))
    email = models.EmailField(blank=True, default='',
                              verbose_name=_("Email"))
    site_web = models.URLField(blank=True, default='',
                               verbose_name=_("Site web"))

    class Meta:
        verbose_name = _("Cabinet")
        verbose_name_plural = _("Cabinets")

    def __str__(self):
        return self.nom


class Partage(models.Model):
    TYPE_CHOICES = [
        ('client', _('Client')),
        ('dossier', _('Dossier')),
    ]
    STATUT_CHOICES = [
        ('en_attente', _('En attente')),
        ('accepte', _('Accepté')),
        ('refuse', _('Refusé')),
    ]

    type_objet = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name=_("Type d'objet"))
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE,
                               null=True, blank=True, related_name='partages',
                               verbose_name=_("Client"))
    dossier = models.ForeignKey('dossiers.Dossier', on_delete=models.CASCADE,
                                null=True, blank=True, related_name='partages',
                                verbose_name=_("Dossier"))
    partage_par = models.ForeignKey(User, on_delete=models.CASCADE,
                                    related_name='partages_crees',
                                    verbose_name=_("Partagé par"))
    partage_avec = models.ForeignKey(User, on_delete=models.CASCADE,
                                     related_name='partages_recus',
                                     verbose_name=_("Partagé avec"))
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES,
                              default='en_attente', verbose_name=_("Statut"))
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("Date"))

    class Meta:
        verbose_name = _("Partage")
        verbose_name_plural = _("Partages")
        ordering = ['-date']

    def __str__(self):
        objet = self.client or self.dossier
        return f"{self.get_type_objet_display()} : {objet} — {self.partage_par} → {self.partage_avec}"
