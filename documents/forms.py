from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from clients.models import Client
from dossiers.models import Dossier
from .models import Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['dossier', 'client', 'categorie', 'commentaire', 'fichier']
        widgets = {'commentaire': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['dossier'].queryset = Dossier.objects.filter(avocat=user).order_by('titre')
        self.fields['client'].queryset = Client.objects.filter(dossiers__avocat=user).distinct().order_by('nom')

    def clean_fichier(self):
        fichier = self.cleaned_data.get('fichier')
        if not fichier:
            raise forms.ValidationError(_("Choisissez un fichier."))
        if fichier.size > settings.UPLOAD_TAILLE_MAX:
            raise forms.ValidationError(_("Fichier trop volumineux (maximum 100 Mo)."))
        nom = fichier.name.lower()
        if not nom.endswith(tuple(settings.UPLOAD_EXTENSIONS)):
            raise forms.ValidationError(_("Type de fichier non autorisé (pdf, docx, jpg, png uniquement)."))
        return fichier


class GenerationDocumentForm(forms.Form):
    dossier = forms.ModelChoiceField(queryset=Dossier.objects.none(), label=_("Dossier"))
    montant_reclame = forms.DecimalField(max_digits=12, decimal_places=2, label=_("Montant réclamé ($)"))
    delai_jours = forms.IntegerField(min_value=1, initial=10, label=_("Délai (jours)"))
    nom_destinataire = forms.CharField(max_length=200, label=_("Nom du destinataire"))
    adresse_destinataire = forms.CharField(max_length=300, required=False, label=_("Adresse du destinataire"))
    adresse_client = forms.CharField(max_length=300, required=False, label=_("Adresse du client"))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['dossier'].queryset = Dossier.objects.filter(avocat=user).order_by('titre')
