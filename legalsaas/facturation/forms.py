from django import forms
from django.utils.translation import gettext_lazy as _
from dossiers.models import Dossier
from .models import EntreeTemps, Paiement


class EntreeTempsForm(forms.ModelForm):
    class Meta:
        model = EntreeTemps
        fields = ['dossier', 'date', 'duree_minutes', 'categorie_activite',
                  'taux_horaire_applique', 'description', 'non_facturable']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, avocat=None, dossier=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].input_formats = ['%Y-%m-%d']
        if avocat is not None:
            self.fields['dossier'].queryset = (
                Dossier.objects.filter(avocat=avocat).select_related('client'))
            self.fields['dossier'].label_from_instance = (
                lambda d: f"{d.client.nom_complet} — {d.titre}")
        if dossier is not None:
            self.fields['dossier'].initial = dossier
            self.fields['dossier'].widget = forms.HiddenInput()
            self.fields['dossier'].required = False


class EntreeTempsEditForm(forms.ModelForm):
    class Meta:
        model = EntreeTemps
        fields = ['date', 'duree_minutes', 'categorie_activite',
                  'taux_horaire_applique', 'description', 'non_facturable']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].input_formats = ['%Y-%m-%d']


class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ['type_paiement', 'date', 'montant', 'methode', 'note']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'note': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].input_formats = ['%Y-%m-%d']
        self.fields['montant'].widget.attrs.update({'min': '0.01', 'step': '0.01'})
