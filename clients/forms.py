from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'type_client', 'prenom', 'nom', 'raison_sociale', 'numero_entreprise',
            'nom_representant', 'email', 'telephone', 'adresse',
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': _("ex. : client@cabinet.com")}),
            'telephone': forms.TextInput(attrs={'placeholder': _("ex. : 514-555-1234")}),
            'adresse': forms.Textarea(attrs={'rows': 3, 'placeholder': _("ex. : 123, rue Principale, Montréal (QC)")}),
        }

    def clean(self):
        cleaned = super().clean()
        type_client = cleaned.get('type_client', 'individu')
        if type_client == 'individu':
            if not (cleaned.get('prenom') or cleaned.get('nom')):
                self.add_error('nom', _("Le nom est requis pour un individu."))
        else:
            if not cleaned.get('raison_sociale'):
                self.add_error('raison_sociale', _("La raison sociale est requise."))
        return cleaned
