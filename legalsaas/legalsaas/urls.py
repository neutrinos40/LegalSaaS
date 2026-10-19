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
from cabinet import views as cabinet_views

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('inscription/', dossiers_views.inscription, name='inscription'),
    path('mot-de-passe/', auth_views.PasswordResetView.as_view(
        template_name='password_reset.html',
        html_email_template_name='password_reset_email.html',
        email_template_name='password_reset_email.html',
        from_email=settings.DEFAULT_FROM_EMAIL,
    ), name='password_reset'),
    path('mot-de-passe/envoye/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'), name='password_reset_done'),
    path('mot-de-passe/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('mot-de-passe/termine/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'), name='password_reset_complete'),
    path('dashboard/', dossiers_views.dashboard, name='dashboard'),
    path('', auth_views.LoginView.as_view(template_name='login.html')),
    path('dossiers/', dossiers_views.liste_dossiers, name='liste_dossiers'),
    path('dossiers/ajouter/', dossiers_views.ajouter_dossier, name='ajouter_dossier'),
    path('clients/', clients_views.liste_clients, name='liste_clients'),
    path('clients/<int:client_id>/', clients_views.fiche_client, name='fiche_client'),
    path('clients/<int:client_id>/modifier/', clients_views.modifier_client, name='modifier_client'),
    path('dossiers/<int:dossier_id>/', dossiers_views.fiche_dossier, name='fiche_dossier'),
    path('dossiers/<int:dossier_id>/chrono/demarrer/', dossiers_views.demarrer_chrono, name='demarrer_chrono'),
    path('dossiers/<int:dossier_id>/chrono/arreter/', dossiers_views.arreter_chrono, name='arreter_chrono'),
    path('dossiers/<int:dossier_id>/chrono/reprendre/', dossiers_views.reprendre_chrono, name='reprendre_chrono'),
    path('dossiers/<int:dossier_id>/chrono/', dossiers_views.arreter_chrono, name='arreter_chrono_base'),
    path('dossiers/<int:dossier_id>/chrono/demarrer/', dossiers_views.demarrer_chrono, name='demarrer_chrono'),
    path('dossiers/<int:dossier_id>/communication/', dossiers_views.ajouter_communication, name='ajouter_communication'),
    path('dossiers/<int:dossier_id>/echeance/', dossiers_views.ajouter_echeance, name='ajouter_echeance'),
    path('dossiers/<int:dossier_id>/temps/', dossiers_views.ajouter_entree_temps, name='ajouter_entree_temps'),
    path('dossiers/<int:dossier_id>/paiement/', dossiers_views.ajouter_paiement, name='ajouter_paiement'),
    path('paiements/<int:paiement_id>/supprimer/', dossiers_views.supprimer_paiement, name='supprimer_paiement'),
    path('dossiers/<int:dossier_id>/documents/ajouter/', dossiers_views.ajouter_document, name='ajouter_document'),
    path('dossiers/<int:dossier_id>/etat-compte/', dossiers_views.exporter_etat_compte, name='exporter_etat_compte'),
    path('dossiers/<int:dossier_id>/modifier/', dossiers_views.modifier_dossier, name='modifier_dossier'),
    path('communications/<int:com_id>/modifier/', dossiers_views.modifier_communication, name='modifier_communication'),
    path('communications/<int:com_id>/supprimer/', dossiers_views.supprimer_communication, name='supprimer_communication'),
    path('echeances/<int:echeance_id>/modifier/', dossiers_views.modifier_echeance, name='modifier_echeance'),
    path('echeances/<int:echeance_id>/supprimer/', dossiers_views.supprimer_echeance, name='supprimer_echeance'),
    path('entrees-temps/<int:entree_id>/modifier/', dossiers_views.modifier_entree_temps, name='modifier_entree_temps'),
    path('entrees-temps/<int:entree_id>/supprimer/', dossiers_views.supprimer_entree_temps, name='supprimer_entree_temps'),
    path('documents/<int:doc_id>/modifier/', dossiers_views.modifier_document, name='modifier_document'),
    path('documents/<int:doc_id>/supprimer/', dossiers_views.supprimer_document, name='supprimer_document'),
    path('reglages/', dossiers_views.reglages, name='reglages'),
    path('echeances/', echeances_views.liste_echeances, name='liste_echeances'),
    path('rendez-vous/', echeances_views.liste_rendezvous, name='liste_rendezvous'),
    path('api/evenements/', echeances_views.api_evenements, name='api_evenements'),
    path('calendrier/rendez-vous/ajouter/', echeances_views.ajouter_rendezvous, name='ajouter_rendezvous'),
    path('calendrier/rendez-vous/<int:rdv_id>/modifier/', echeances_views.modifier_rendezvous, name='modifier_rendezvous'),
    path('calendrier/tache/ajouter/', echeances_views.ajouter_tache, name='ajouter_tache'),
    path('calendrier/tache/<int:tache_id>/modifier/', echeances_views.modifier_tache, name='modifier_tache'),
    path('calendrier/tache/<int:tache_id>/basculer/', echeances_views.basculer_tache, name='basculer_tache'),
    path('documents/', documents_views.liste_documents, name='liste_documents'),
    path('documents/generes/', documents_views.liste_documents_generes, name='liste_documents_generes'),
    path('documents/generer/', documents_views.generer_document, name='generer_document'),
    path('documents/reviser/<int:pk>/', documents_views.reviser_document, name='reviser_document'),
    path('documents/exporter/<int:pk>/<str:format>/', documents_views.exporter_document, name='exporter_document'),
    path('documents/analyser/<int:document_id>/', documents_views.analyser_document, name='analyser_document'),
    path('documents/analyse/<int:analyse_id>/', documents_views.fiche_analyse, name='fiche_analyse'),
    path('documents/analyse/<int:analyse_id>/export/<str:format>/', documents_views.exporter_analyse, name='exporter_analyse'),
    path('facturation/', facturation_views.liste_facturation, name='liste_facturation'),
    path('facturation/generer/<int:client_id>/', facturation_views.generer_facture_client, name='generer_facture_client'),
    path('cabinet/', cabinet_views.gestion_cabinet, name='gestion_cabinet'),
    path('cabinet/creer/', cabinet_views.creer_cabinet, name='creer_cabinet'),
    path('cabinet/rejoindre/', cabinet_views.rejoindre_cabinet, name='rejoindre_cabinet'),
    path('cabinet/partager/', cabinet_views.partager_objet, name='partager_objet'),
    path('cabinet/partage/<int:partage_id>/', cabinet_views.repondre_partage, name='repondre_partage'),
    path('dossiers/ajouter/', dossiers_views.ajouter_dossier, name='ajouter_dossier'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
