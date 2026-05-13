from django.shortcuts import render
from rest_framework import viewsets, filters
from .models import *
from .serializers import *
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework import status

class EleitorViewSet(viewsets.ModelViewSet):
    queryset = Eleitor.objects.all()
    serializer_class = EleitorSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nome', 'email', 'cpf']
    ordering_fields = ['nome', 'data_cadastro']
    ordering = ['nome']

class EleicaoViewSet(viewsets.ModelViewSet):
    queryset = Eleicao.objects.all()
    serializer_class = EleicaoSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['titulo']
    ordering_fields = ['data_inicio']
    ordering = ['data_inicio']


class CandidatoViewSet(viewsets.ModelViewSet):
    queryset = Candidato.objects.select_related('eleicao').all()
    serializer_class = CandidatoSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nome', 'nome_urna', 'partido_ou_chapa']
    

class AptidaoEleitorViewSet(viewsets.ModelViewSet):
    queryset = AptidaoEleitor.objects.select_related('eleitor', 'eleicao').all()
    serializer_class = ApitidaoEleitorSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['eleitor__nome', 'eleicao__titulo']
    

class RegistroVotacaoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RegistroVotacao.objects.all().order_by('-data_hora')
    serializer_class = RegistroVotacaoSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['eleicao__titulo']
    ordering_fields = ['data_hora']
    ordering = ['-data_hora']
     
class VotoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Voto.objects.all()
    serializer_class = VotoSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['eleicao__titulo']
    