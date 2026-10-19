from django import forms
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Communication, Dossier
from clients.models import Client


def clients_accessibles(user):
    dossiers_accessibles = Dossier.objects.filter(
        Q(avocat=user) | Q(partages__partage_avec=user, partages__statut='accepte')
    ).distinct()
    return Client.objects.filter(
        Q(avocat=user)
        | Q(id__in=dossiers_accessibles.values('client_id'))
        | Q(id__in=[
            p.client_id for p in user.partages_recus.filter(
                type_objet='client', statut='accepte')
        ])
    ).distinct().order_by('nom', 'prenom', 'raison_sociale')


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


class DossierCreationForm(forms.Form):
    type_client = forms.ChoiceField(
        choices=Client.TYPE_CLIENT_CHOICES, initial='individu',
        label=_("Type de client"))
    nom_complet = forms.CharField(
        max_length=200, required=False, label=_("Nom complet"),
        widget=forms.TextInput(attrs={'placeholder': _("Nom et prénom, ou raison sociale")}))
    email = forms.EmailField(required=False, label=_("Courriel"))
    telephone = forms.CharField(max_length=20, required=False, label=_("Téléphone"))

    client_existant = forms.ModelChoiceField(
        queryset=Client.objects.none(), required=False,
        label=_("Rattacher à un client existant"))

    titre = forms.CharField(
        max_length=200, required=False, label=_("Titre du dossier"),
        help_text=_("Laissez vide pour un titre automatique."))
    type_procedure = forms.ChoiceField(
        choices=Dossier.TYPE_PROCEDURE_CHOICES, label=_("Procédure"))
    date_debut = forms.DateField(
        label=_("Début de la procédure"), initial=timezone.localdate,
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    statut = forms.ChoiceField(
        choices=Dossier.STATUT_CHOICES, initial='actif', label=_("Statut"))
    notes = forms.CharField(
        required=False, label=_("Notes"),
        widget=forms.Textarea(attrs={'rows': 3}))

    echeance_type = forms.CharField(
        max_length=100, required=False, label=_("Type d'échéance"),
        widget=forms.TextInput(attrs={'list': 'suggestions-echeance',
                                      'autocomplete': 'off'}),
        help_text=_("Facultatif. Ex. : dépôt de la défense."))
    echeance_date = forms.DateField(
        required=False, label=_("Date de l'échéance"),
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['client_existant'].queryset = clients_accessibles(user)
        self.fields['date_debut'].input_formats = ['%Y-%m-%d']
        self.fields['echeance_date'].input_formats = ['%Y-%m-%d']

    def clean(self):
        data = super().clean()
        if not data.get('client_existant') and not (data.get('nom_complet') or '').strip():
            self.add_error('nom_complet', _(
                "Indiquez le nom du client ou sélectionnez un client existant."))
        if data.get('echeance_type') and not data.get('echeance_date'):
            self.add_error('echeance_date', _("Précisez la date de l'échéance."))
        if data.get('echeance_date') and not data.get('echeance_type'):
            self.add_error('echeance_type', _("Précisez le type d'échéance."))
        return data


class DossierForm(forms.ModelForm):
    class Meta:
        model = Dossier
        fields = ['client', 'titre', 'type_procedure', 'statut',
                  'date_debut', 'notes']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['client'].queryset = clients_accessibles(user)
        self.fields['date_debut'].input_formats = ['%Y-%m-%d']
