from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from clients.models import Client
from dossiers.models import Dossier


def chemin_upload(instance, nom_fichier):
    dossier = instance.dossier_id or "sans_dossier"
    return f"documents/dossier_{dossier}/{nom_fichier}"


class Document(models.Model):
    CATEGORIE_CHOICES = [
        ('avis_juridique', _('Avis juridique')),
        ('contrat', _('Contrat')),
        ('correspondance', _('Correspondance')),
        ('preuve', _('Preuve')),
        ('autre', _('Autre')),
    ]

    dossier = models.ForeignKey(Dossier, on_delete=models.SET_NULL, related_name='documents', blank=True, null=True)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, related_name='documents', blank=True, null=True)
    fichier = models.FileField(upload_to=chemin_upload, verbose_name=_("Fichier"))
    nom_original = models.CharField(max_length=255, verbose_name=_("Nom original"))
    categorie = models.CharField(max_length=30, choices=CATEGORIE_CHOICES, default='autre', verbose_name=_("Catégorie"))
    date_upload = models.DateTimeField(auto_now_add=True, verbose_name=_("Date d'upload"))
    taille_octets = models.PositiveIntegerField(blank=True, null=True, verbose_name=_("Taille (octets)"))
    type_fichier = models.CharField(max_length=10, blank=True, default='', verbose_name=_("Type de fichier"))
    auteur = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True,
                               related_name='documents_uploades', verbose_name=_("Auteur"))
    commentaire = models.TextField(blank=True, null=True, verbose_name=_("Commentaire"))

    def __str__(self):
        return self.nom_original


class DocumentGenere(models.Model):
    TYPE_DOCUMENT_CHOICES = [
        ('mise_en_demure', _('Mise en demeure')),
    ]

    STATUT_CHOICES = [
        ('brouillon', _('Brouillon')),
        ('valide', _('Validé')),
        ('rejete', _('Rejeté')),
        ('envoye', _('Envoyé')),
    ]

    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name='documents_generes')
    type_document = models.CharField(max_length=50, choices=TYPE_DOCUMENT_CHOICES,
                                     default='mise_en_demure', verbose_name=_("Type de document"))
    contenu_brouillon = models.TextField(verbose_name=_("Contenu du brouillon"))
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES,
                              default='brouillon', verbose_name=_("Statut"))
    date_generation = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de génération"))
    date_validation = models.DateTimeField(null=True, blank=True, verbose_name=_("Date de validation"))
    valide_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='documents_valides', verbose_name=_("Validé par"))
    parametres_generation = models.TextField(blank=True, default='', verbose_name=_("Paramètres de génération"))

    def __str__(self):
        return f"{self.get_type_document_display()} - {self.dossier} ({self.get_statut_display()})"


class JournalDocumentGenere(models.Model):
    ACTION_CHOICES = [
        ('generation', _('Génération')),
        ('modification', _('Modification')),
        ('validation', _('Validation')),
        ('rejet', _('Rejet')),
    ]

    document = models.ForeignKey(DocumentGenere, on_delete=models.CASCADE, related_name='journal')
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_("Utilisateur"))
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name=_("Action"))
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("Date"))
    details = models.TextField(blank=True, default='', verbose_name=_("Détails"))

    def __str__(self):
        return f"{self.get_action_display()} - {self.document} - {self.date}"


class AnalyseDocument(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='analyses')
    contenu_analyse = models.TextField(verbose_name=_("Analyse"))
    date_analyse = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de l'analyse"))
    auteur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='analyses_documents', verbose_name=_("Auteur"))

    def __str__(self):
        return f"Analyse de {self.document} — {self.date_analyse}"
