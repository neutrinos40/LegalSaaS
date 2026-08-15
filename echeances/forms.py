from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Echeance


class EcheanceForm(forms.ModelForm):
    class Meta:
        model = Echeance
        fields = ['type_delai', 'date_limite', 'description']
        widgets = {
            'type_delai': forms.TextInput(attrs={'placeholder': _("ex. : Dépôt de conclusions")}),
            'date_limite': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': _("Détails de l'échéance…")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_limite'].input_formats = ['%Y-%m-%d']
