from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext as _

from .forms import ClientForm
from .models import Client


def _clients_accesibles(user):
    """Clients visibles par l'avocat : les siens + ceux partagés avec lui."""
    from cabinet.models import Partage
    return Client.objects.filter(
        Q(avocat=user) | Q(partages__partage_avec=user, partages__statut='accepte')
    ).annotate(
        nb_dossiers=Count('dossiers', filter=Q(dossiers__avocat=user))
    ).distinct()


@login_required
def liste_clients(request):
    q = request.GET.get('q', '').strip()
    clients = _clients_accesibles(request.user).order_by('nom', 'prenom')

    if q:
        clients = clients.filter(
            Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(raison_sociale__icontains=q)
            | Q(nom_representant__icontains=q) | Q(email__icontains=q)
        )

    form = ClientForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        client = form.save(commit=False)
        client.avocat = request.user
        client.save()
        messages.success(request, _("Client ajouté avec succès."))
        return redirect('fiche_client', client_id=client.pk)

    context = {
        'clients': clients,
        'q': q,
        'form': form,
        'active': 'clients',
    }
    return render(request, 'clients_liste.html', context)


@login_required
def modifier_client(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    from dossiers.forms import clients_accessibles
    if not clients_accessibles(request.user).filter(id=client.id).exists():
        messages.error(request, _("Vous n'avez pas accès à ce client."))
        return redirect('liste_clients')
    retour = (request.GET.get('next') or request.POST.get('next')
              or reverse('fiche_client', args=[client.id]))
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, _("Client modifié."))
            return redirect(retour)
    else:
        form = ClientForm(instance=client)
    return render(request, 'element_modifier.html', {
        'form': form,
        'titre': _("Modifier le client"),
        'retour': retour,
        'next': retour,
    })


@login_required
def fiche_client(request, client_id):
    client = get_object_or_404(
        Client.objects.prefetch_related('dossiers__documents'),
        id=client_id,
    )
    if not _clients_accesibles(request.user).filter(id=client.id).exists():
        messages.error(request, _("Vous n'avez pas accès à ce client."))
        return redirect('liste_clients')

    from dossiers.views import get_profil
    profil = get_profil(request.user)
    dossiers = client.dossiers.filter(
        Q(avocat=request.user) | Q(partages__partage_avec=request.user, partages__statut='accepte')
    ).distinct().order_by('-date_debut')
    documents = client.documents.filter(
        Q(dossier__avocat=request.user) | Q(auteur=request.user)
        | Q(dossier__partages__partage_avec=request.user, dossier__partages__statut='accepte')
    ).distinct().order_by('-date_upload')[:20]

    from cabinet.models import Partage
    partages_client = Partage.objects.filter(
        type_objet='client', client=client
    ).select_related('partage_avec', 'partage_par')

    from django.contrib.auth.models import User as UserModel
    if profil.cabinet:
        membres_cabinet = UserModel.objects.filter(
            profil__cabinet=profil.cabinet
        ).exclude(id=request.user.id)
    else:
        membres_cabinet = UserModel.objects.none()

    est_proprietaire = (client.avocat == request.user)

    context = {
        'client': client,
        'dossiers': dossiers,
        'documents': documents,
        'partages_client': partages_client,
        'membres_cabinet': membres_cabinet,
        'est_proprietaire': est_proprietaire,
        'active': 'clients',
    }
    return render(request, 'fiche_client.html', context)
