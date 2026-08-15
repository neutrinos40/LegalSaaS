from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext as _

from .forms import ClientForm
from .models import Client


def _clients_avocat(avocat):
    return (Client.objects
            .filter(Q(avocat=avocat) | Q(dossiers__avocat=avocat))
            .annotate(nb_dossiers=Count('dossiers', filter=Q(dossiers__avocat=avocat)))
            .distinct())


@login_required
def liste_clients(request):
    q = request.GET.get('q', '').strip()
    clients = _clients_avocat(request.user).order_by('nom', 'prenom')

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
def fiche_client(request, client_id):
    client = get_object_or_404(
        Client.objects.prefetch_related('dossiers__documents'),
        id=client_id,
    )
    if not _clients_avocat(request.user).filter(id=client.id).exists():
        messages.error(request, _("Vous n'avez pas accès à ce client."))
        return redirect('liste_clients')

    dossiers = client.dossiers.filter(avocat=request.user).order_by('-date_debut')
    documents = client.documents.filter(
        Q(dossier__avocat=request.user) | Q(auteur=request.user)
    ).order_by('-date_upload')[:20]

    context = {
        'client': client,
        'dossiers': dossiers,
        'documents': documents,
        'active': 'clients',
    }
    return render(request, 'fiche_client.html', context)
