from django.contrib import admin
from .models import Document, AnalyseDocument


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('nom_original', 'dossier', 'client', 'categorie', 'taille_octets', 'auteur', 'date_upload')
    list_filter = ('categorie', 'type_fichier', 'date_upload')
    search_fields = ('nom_original', 'commentaire')


@admin.register(AnalyseDocument)
class AnalyseDocumentAdmin(admin.ModelAdmin):
    list_display = ('document', 'auteur', 'date_analyse')
    list_filter = ('date_analyse',)
    search_fields = ('document__nom_original',)
