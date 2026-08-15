"""
URL configuration for legalsaas project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from dossiers import views as dossiers_views
from echeances import views as echeances_views
from documents import views as documents_views
from clients import views as clients_views
from facturation import views as facturation_views    

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', dossiers_views.dashboard, name='dashboard'),
    path('', auth_views.LoginView.as_view(template_name='login.html')),
    path('dossiers/', dossiers_views.liste_dossiers, name='liste_dossiers'),
    path('clients/', clients_views.liste_clients, name='liste_clients'),
    path('clients/<int:client_id>/', clients_views.fiche_client, name='fiche_client'),
    path('dossiers/<int:dossier_id>/', dossiers_views.fiche_dossier, name='fiche_dossier'),
    path('dossiers/<int:dossier_id>/chrono/', dossiers_views.arreter_chrono, name='arreter_chrono'),
    path('dossiers/<int:dossier_id>/chrono/demarrer/', dossiers_views.demarrer_chrono, name='demarrer_chrono'),
    path('dossiers/<int:dossier_id>/communication/', dossiers_views.ajouter_communication, name='ajouter_communication'),
    path('dossiers/<int:dossier_id>/echeance/', dossiers_views.ajouter_echeance, name='ajouter_echeance'),
    path('dossiers/<int:dossier_id>/temps/', dossiers_views.ajouter_entree_temps, name='ajouter_entree_temps'),
    path('dossiers/<int:dossier_id>/documents/ajouter/', dossiers_views.ajouter_document, name='ajouter_document'),
    path('dossiers/<int:dossier_id>/etat-compte/', dossiers_views.exporter_etat_compte, name='exporter_etat_compte'),
    path('reglages/', dossiers_views.reglages, name='reglages'),
    path('echeances/', echeances_views.liste_echeances, name='liste_echeances'),
    path('rendez-vous/', echeances_views.liste_rendezvous, name='liste_rendezvous'),
    path('api/evenements/', echeances_views.api_evenements, name='api_evenements'),
    path('documents/', documents_views.liste_documents, name='liste_documents'),
    path('documents/generes/', documents_views.liste_documents_generes, name='liste_documents_generes'),
    path('documents/generer/', documents_views.generer_document, name='generer_document'),
    path('documents/reviser/<int:pk>/', documents_views.reviser_document, name='reviser_document'),
    path('documents/exporter/<int:pk>/<str:format>/', documents_views.exporter_document, name='exporter_document'),
    path('documents/analyser/<int:document_id>/', documents_views.analyser_document, name='analyser_document'),
    path('documents/analyse/<int:analyse_id>/', documents_views.fiche_analyse, name='fiche_analyse'),
    path('documents/analyse/<int:analyse_id>/export/<str:format>/', documents_views.exporter_analyse, name='exporter_analyse'),
    path('api/evenements/', echeances_views.api_evenements, name='api_evenements'),
    path('facturation/', facturation_views.liste_facturation, name='liste_facturation'),
    path('facturation/generer/<int:client_id>/', facturation_views.generer_facture_client, name='generer_facture_client'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)