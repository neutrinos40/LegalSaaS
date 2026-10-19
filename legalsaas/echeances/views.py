from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import Echeance, RendezVous, Tache


def _dossiers_accesibles(user):
    from dossiers.models import Dossier
    return Dossier.objects.filter(
        Q(avocat=user) | Q(partages__partage_avec=user, partages__statut='accepte')
    ).distinct()


@login_required
def liste_echeances(request):
    echeances = Echeance.objects.filter(
        dossier__in=_dossiers_accesibles(request.user)
    ).order_by('date_limite')
    return render(request, 'echeances_liste.html', {'echeances': echeances, 'active': 'echeances'})


@login_required
def liste_rendezvous(request):
    rendez_vous = RendezVous.objects.filter(
        dossier__in=_dossiers_accesibles(request.user)
    ).order_by('date_heure')
    return render(request, 'rendezvous_liste.html', {'rendez_vous': rendez_vous, 'active': 'rendezvous'})


@login_required
def api_evenements(request):
    """API JSON pour FullCalendar — retourne échéances + rendez-vous + tâches accessibles."""
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    dossiers = _dossiers_accesibles(request.user)

    events = []

    qs_echeances = Echeance.objects.select_related('dossier', 'dossier__client').filter(
        dossier__in=dossiers
    )
    if start_str:
        qs_echeances = qs_echeances.filter(date_limite__gte=start_str[:10])
    if end_str:
        qs_echeances = qs_echeances.filter(date_limite__lte=end_str[:10])

    for e in qs_echeances:
        events.append({
            'id': f'echeance-{e.pk}',
            'title': f"⚖ {e.type_delai}",
            'start': e.date_limite.isoformat(),
            'allDay': True,
            'url': f"/dossiers/{e.dossier.pk}/",
            'className': 'echeance',
            'extendedProps': {
                'type': 'echeance',
                'type_delai': e.type_delai,
                'dossier': e.dossier.titre,
                'statut': e.statut,
                'statut_label': e.get_statut_display(),
                'description': e.description,
            }
        })

    qs_rdv = RendezVous.objects.select_related('client', 'dossier').filter(
        dossier__in=dossiers
    )
    if start_str:
        qs_rdv = qs_rdv.filter(date_heure__date__gte=start_str[:10])
    if end_str:
        qs_rdv = qs_rdv.filter(date_heure__date__lte=end_str[:10])

    for rdv in qs_rdv:
        end_dt = rdv.date_heure + timezone.timedelta(hours=1)
        events.append({
            'id': f'rdv-{rdv.pk}',
            'title': f"📅 {rdv.client.nom_complet}",
            'start': rdv.date_heure.isoformat(),
            'end': end_dt.isoformat(),
            'allDay': False,
            'url': f"/dossiers/{rdv.dossier.pk}/" if rdv.dossier else f"/clients/{rdv.client.pk}/",
            'className': f"rdv {rdv.statut}",
            'extendedProps': {
                'type': 'rdv',
                'rdv_id': rdv.pk,
                'client': rdv.client.nom_complet,
                'mode': rdv.get_mode_display(),
                'lieu_ou_lien': rdv.lieu_ou_lien or '',
                'statut': rdv.statut,
                'statut_label': rdv.get_statut_display(),
                'notes': rdv.notes or '',
            }
        })

    qs_taches = Tache.objects.select_related('dossier', 'client').filter(avocat=request.user)
    if start_str:
        qs_taches = qs_taches.filter(date_echeance__gte=start_str[:10])
    if end_str:
        qs_taches = qs_taches.filter(date_echeance__lte=end_str[:10])

    for t in qs_taches:
        events.append({
            'id': f'tache-{t.pk}',
            'title': f"✓ {t.titre}",
            'start': t.date_echeance.isoformat() if t.date_echeance else None,
            'allDay': True,
            'url': f"/dossiers/{t.dossier.pk}/" if t.dossier else '',
            'className': f"tache {t.priorite}" + (" terminee" if t.terminee else ""),
            'extendedProps': {
                'type': 'tache',
                'titre': t.titre,
                'description': t.description,
                'priorite': t.priorite,
                'priorite_label': t.get_priorite_display(),
                'terminee': t.terminee,
                'dossier': t.dossier.titre if t.dossier else '',
                'tache_id': t.pk,
            }
        })

    return JsonResponse(events, safe=False)


@login_required
def ajouter_rendezvous(request):
    from .forms import RendezVousForm
    if request.method == 'POST':
        form = RendezVousForm(request.POST, user=request.user)
        if form.is_valid():
            rdv = form.save(commit=False)
            rdv.avocat = request.user
            rdv.save()
            messages.success(request, _("Rendez-vous ajouté."))
        else:
            messages.error(request, _("Erreur dans le formulaire de rendez-vous."))
    return redirect(request.POST.get('next') or 'dashboard')


@login_required
def modifier_rendezvous(request, rdv_id):
    from .forms import RendezVousForm
    rdv = get_object_or_404(RendezVous, pk=rdv_id, avocat=request.user)
    if request.method == 'POST':
        form = RendezVousForm(request.POST, instance=rdv, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Rendez-vous modifié."))
            return redirect(request.POST.get('next') or 'dashboard')
    else:
        form = RendezVousForm(instance=rdv, user=request.user)
    return render(request, 'echeances/modifier_rendezvous.html', {
        'form': form,
        'rdv': rdv,
        'next': request.GET.get('next') or request.META.get('HTTP_REFERER', ''),
    })


@login_required
def ajouter_tache(request):
    from .forms import TacheForm
    if request.method == 'POST':
        form = TacheForm(request.POST, user=request.user)
        if form.is_valid():
            tache = form.save(commit=False)
            tache.avocat = request.user
            if tache.dossier:
                tache.client = tache.dossier.client
            tache.save()
            messages.success(request, _("Tâche ajoutée."))
        else:
            messages.error(request, _("Erreur dans le formulaire de tâche."))
    return redirect(request.POST.get('next') or 'dashboard')


@login_required
def modifier_tache(request, tache_id):
    from .forms import TacheForm
    tache = get_object_or_404(Tache, pk=tache_id, avocat=request.user)
    if request.method == 'POST':
        form = TacheForm(request.POST, instance=tache, user=request.user)
        if form.is_valid():
            tache = form.save(commit=False)
            if tache.dossier:
                tache.client = tache.dossier.client
            tache.save()
            messages.success(request, _("Tâche modifiée."))
            return redirect(request.POST.get('next') or 'dashboard')
    else:
        form = TacheForm(instance=tache, user=request.user)
    return render(request, 'echeances/modifier_tache.html', {
        'form': form,
        'tache': tache,
        'next': request.GET.get('next') or request.META.get('HTTP_REFERER', ''),
    })


@login_required
def basculer_tache(request, tache_id):
    tache = Tache.objects.filter(pk=tache_id, avocat=request.user).first()
    if tache:
        tache.terminee = not tache.terminee
        tache.save()
    return redirect(request.POST.get('next') or 'dashboard')
