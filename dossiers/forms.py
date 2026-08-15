from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Communication


class CommunicationForm(forms.ModelForm):
    class Meta:
        model = Communication
        fields = ['type_communication', 'date', 'description']
        widgets = {
            'date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].input_formats = ['%Y-%m-%dT%H:%M']
