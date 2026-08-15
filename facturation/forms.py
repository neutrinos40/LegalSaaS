from django import forms
from django.utils.translation import gettext_lazy as _
from dossiers.models import Dossier
from .models import EntreeTemps


class EntreeTempsForm(forms.ModelForm):
    class Meta:
        model = EntreeTemps
        fields = ['dossier', 'date', 'duree_minutes', 'categorie_activite',
                  'taux_horaire_applique', 'description', 'non_facturable']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, avocat=None, **kwargs):
        super().__init__(*args, **kwargs)
        if avocat is not None:
            self.fields['dossier'].queryset = (
                Dossier.objects.filter(avocat=avocat).select_related('client'))
            self.fields['dossier'].label_from_instance = (
                lambda d: f"{d.client.nom_complet} — {d.titre}")