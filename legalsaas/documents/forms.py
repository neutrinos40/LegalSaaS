from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from dossiers.models import Dossier
from .models import Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['dossier', 'categorie', 'commentaire', 'fichier']
        widgets = {'commentaire': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        from dossiers.views import _dossiers_accesibles
        self.fields['dossier'].queryset = _dossiers_accesibles(user).select_related(
            'client').order_by('titre')
        self.fields['dossier'].required = True
        self.fields['dossier'].label = _("Dossier (obligatoire)")
        self.fields['dossier'].empty_label = _("— Choisir un dossier —")
        self.fields['dossier'].label_from_instance = (
            lambda d: f"{d.client.nom_complet} — {d.titre}")

    def clean(self):
        cleaned = super().clean()
        dossier = cleaned.get('dossier')
        if dossier:
            cleaned['client'] = dossier.client
        return cleaned

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


class DocumentEditForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['nom_original', 'categorie', 'commentaire']
        widgets = {'commentaire': forms.Textarea(attrs={'rows': 2})}


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
