from collections import defaultdict
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from clients.models import Client
from .forms import EntreeTempsForm
from .models import Abonnement, EntreeTemps, Facture, UsageIA


@login_required
def liste_facturation(request):
    aujourd_hui = timezone.now()
    form = EntreeTempsForm(request.POST or None, avocat=request.user)
    if request.method == 'POST' and 'prestation' in request.POST and form.is_valid():
        entree = form.save(commit=False)
        entree.avocat = request.user
        entree.saisie_manuelle = True
        entree.save()
        messages.success(request, _("Prestation ajoutée et prête à facturer."))
        return redirect('liste_facturation')
    abonnement, _created = Abonnement.objects.get_or_create(avocat=request.user)
    usages_mois = UsageIA.objects.filter(avocat=request.user, date__year=aujourd_hui.year, date__month=aujourd_hui.month)
    nb_appels_ia = usages_mois.count()
    factures = Facture.objects.filter(avocat=request.user).order_by('-mois')[:12]
    entrees = EntreeTemps.objects.filter(avocat=request.user, non_facturable=False).select_related('dossier', 'dossier__client').order_by('-date')
    par_client = defaultdict(list)
    for e in entrees:
        par_client[e.dossier.client].append(e)
    factures_par_client = []
    for client, lignes in par_client.items():
        dossiers = []
        for l in lignes:
            if l.dossier not in dossiers:
                dossiers.append(l.dossier)
        factures_par_client.append({'client': client, 'lignes': lignes,
                                    'dossiers': dossiers,
                                    'total': sum(l.montant for l in lignes)})
    return render(request, 'facturation_liste.html', {
        'form': form,
        'abonnement': abonnement,
        'nb_appels_ia': nb_appels_ia,
        'quota_restant': max(abonnement.quota_mensuel - nb_appels_ia, 0),
        'factures': factures,
        'factures_par_client': factures_par_client,
        'today': aujourd_hui,
        'active': 'facturation',
    })


@login_required
def generer_facture_client(request, client_id):
    aujourd_hui = timezone.now()
    mois = aujourd_hui.strftime('%Y-%m')
    client = get_object_or_404(Client, id=client_id)
    total = EntreeTemps.objects.filter(
        avocat=request.user, dossier__client=client,
        non_facturable=False,
        date__year=aujourd_hui.year, date__month=aujourd_hui.month,
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    if total > 0:
        Facture.objects.update_or_create(
            avocat=request.user, client=client, mois=mois,
            defaults={'montant': total},
        )
        messages.success(request, _("Facture générée pour %(c)s (%(m)s)") % {'c': client.nom_complet, 'm': mois})
    else:
        messages.warning(request, _("Aucune prestation à facturer ce mois-ci pour %(c)s.") % {'c': client.nom_complet})
    return redirect('liste_facturation')
