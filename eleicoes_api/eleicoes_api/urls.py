"""
URL configuration for eleicoes_api project.

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

from rest_framework.routers import DefaultRouter
from urna.views import *

from drf_yasg.views import get_schema_view
from drf_yasg import openapi

router = DefaultRouter()
router.register(r'eleitores', EleitorViewSet, basename='eleitores')
router.register(r'eleicoes', EleicaoViewSet, basename='eleicoes')
router.register(r'candidatos', CandidatoViewSet, basename='candidatos')
router.register(r'aptidoes', AptidaoEleitorViewSet, basename='aptidoes')
router.register(r'registros-votacao', RegistroVotacaoViewSet, basename='registros-votacao')
router.register(r'votos', VotoViewSet, basename='votos')

schema_view = get_schema_view(
   openapi.Info(
      title="Eleicoes API",
      default_version='v1',
      description="API para gerenciamento de eleições, candidatos e votações",
      contact=openapi.Contact(email="contato@eleicoesapi.com"),
   ),
   public=True, 
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('eleicoes_api/', include(router.urls)),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
