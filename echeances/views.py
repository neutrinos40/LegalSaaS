from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from .models import Echeance, RendezVous


@login_required
def liste_echeances(request):
    echeances = Echeance.objects.filter(dossier__avocat=request.user).order_by('date_limite')
    return render(request, 'echeances_liste.html', {'echeances': echeances, 'active': 'echeances'})


@login_required
def liste_rendezvous(request):
    rendez_vous = RendezVous.objects.filter(avocat=request.user).order_by('date_heure')
    return render(request, 'rendezvous_liste.html', {'rendez_vous': rendez_vous, 'active': 'rendezvous'})


@login_required
def api_evenements(request):
    """API JSON pour FullCalendar - retourne échéances + rendez-vous de l'avocat connecté."""
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')

    events = []

    # Échéances
    qs_echeances = Echeance.objects.select_related('dossier', 'dossier__client').filter(
        dossier__avocat=request.user
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

    # Rendez-vous
    qs_rdv = RendezVous.objects.select_related('client', 'dossier').filter(avocat=request.user)
    if start_str:
        qs_rdv = qs_rdv.filter(date_heure__date__gte=start_str[:10])
    if end_str:
        qs_rdv = qs_rdv.filter(date_heure__date__lte=end_str[:10])

    for rdv in qs_rdv:
        end_dt = rdv.date_heure + timezone.timedelta(hours=1)  # durée par défaut 1h
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
                'client': rdv.client.nom_complet,
                'mode': rdv.get_mode_display(),
                'lieu_ou_lien': rdv.lieu_ou_lien or '',
                'statut': rdv.statut,
                'statut_label': rdv.get_statut_display(),
                'notes': rdv.notes or '',
            }
        })

    return JsonResponse(events, safe=False)