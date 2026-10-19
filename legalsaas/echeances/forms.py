from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Echeance, RendezVous, Tache
from .regles_delais import REGLES_DELAIS

MODE_CHOICES = [
    ('manuel', _("Saisie manuelle de la date")),
    ('automatique', _("Calcul automatique")),
]

TYPE_PROCEDURE_CHOICES = [(cle, regle['description']) for cle, regle in REGLES_DELAIS.items()]


class EcheanceForm(forms.ModelForm):
    mode_saisie = forms.ChoiceField(
        choices=MODE_CHOICES, initial='manuel', widget=forms.RadioSelect,
        label=_("Mode de saisie"))
    type_procedure = forms.ChoiceField(
        choices=TYPE_PROCEDURE_CHOICES, required=False,
        label=_("Type de délai (calcul automatique)"))
    date_depart = forms.DateField(
        required=False, widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        label=_("Date de départ du délai"))

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
        self.fields['date_depart'].input_formats = ['%Y-%m-%d']
        # Ces champs deviennent optionnels au niveau du formulaire :
        # leur obligation dépend du mode choisi (voir clean())
        self.fields['type_delai'].required = False
        self.fields['date_limite'].required = False
        self.fields['mode_saisie'].required = False
        self.order_fields(['mode_saisie', 'type_delai', 'date_limite',
                           'type_procedure', 'date_depart', 'description'])

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get('mode_saisie') or 'manuel'
        cleaned['mode_saisie'] = mode
        if mode == 'manuel':
            if not cleaned.get('type_delai'):
                self.add_error('type_delai', _("Ce champ est requis en saisie manuelle."))
            if not cleaned.get('date_limite'):
                self.add_error('date_limite', _("Ce champ est requis en saisie manuelle."))
        else:
            if not cleaned.get('type_procedure'):
                self.add_error('type_procedure', _("Choisissez un type de délai."))
            if not cleaned.get('date_depart'):
                self.add_error('date_depart', _("La date de départ est requise."))
        return cleaned


class RendezVousForm(forms.ModelForm):
    class Meta:
        model = RendezVous
        fields = ['client', 'dossier', 'date_heure', 'mode', 'lieu_ou_lien', 'notes', 'statut']
        widgets = {
            'date_heure': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        dossier = kwargs.pop('dossier', None)
        super().__init__(*args, **kwargs)
        from django.db.models import Q
        from clients.models import Client
        from dossiers.models import Dossier

        if user is not None:
            dossiers_accessibles = Dossier.objects.filter(
                Q(avocat=user) | Q(partages__partage_avec=user, partages__statut='accepte')
            ).distinct()
            self.fields['client'].queryset = Client.objects.filter(
                Q(avocat=user)
                | Q(partages__partage_avec=user, partages__statut='accepte')
                | Q(dossiers__in=dossiers_accessibles)
            ).distinct()
            self.fields['dossier'].queryset = dossiers_accessibles
        self.fields['dossier'].required = False
        if dossier:
            self.fields['dossier'].initial = dossier
            self.fields['client'].initial = dossier.client
            self.fields['dossier'].widget = forms.HiddenInput()
            self.fields['client'].widget = forms.HiddenInput()
        self.fields['date_heure'].input_formats = ['%Y-%m-%dT%H:%M']


class TacheForm(forms.ModelForm):
    class Meta:
        model = Tache
        fields = ['titre', 'description', 'date_echeance', 'priorite', 'dossier']
        widgets = {
            'date_echeance': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.Textarea(attrs={'rows': 3}),
            'titre': forms.TextInput(attrs={'placeholder': _("ex. : Préparer les conclusions")}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        dossier = kwargs.pop('dossier', None)
        super().__init__(*args, **kwargs)
        from django.db.models import Q
        from dossiers.models import Dossier

        if user is not None:
            self.fields['dossier'].queryset = Dossier.objects.filter(
                Q(avocat=user) | Q(partages__partage_avec=user, partages__statut='accepte')
            ).distinct()
        self.fields['dossier'].required = False
        self.fields['date_echeance'].input_formats = ['%Y-%m-%d']
        if dossier:
            self.fields['dossier'].initial = dossier
            self.fields['dossier'].widget = forms.HiddenInput()