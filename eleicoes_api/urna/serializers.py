from .models import *
from rest_framework import serializers
import re
from django.utils import timezone

class EleitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Eleitor
        fields = "__all__"
    def validate_cpf(self, value):
        if not re.match(r'^\d{3}\.\d{3}\.\d{3}-\d{2}$', value):
            raise serializers.ValidationError("CPF deve estar no formato 000.000.000-00")
        return value

class EleicaoSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_candidatos = serializers.SerializerMethodField()
    total_aptos = serializers.SerializerMethodField()

    class Meta:
        model = Eleicao
        fields = "__all__"

    def get_total_candidatos(self, obj):
        return obj.candidatos.count()

    def get_total_aptos(self, obj):
        return obj.aptos.count()
    
class CandidatoSerializer(serializers.ModelSerializer):
    eleicao_titulo = serializers.CharField(source='eleicao.titulo', read_only=True)

    class Meta:
        model = Candidato
        fields = "__all__"

    def validate_numero(self, value):
        if value == 0:
            raise serializers.ValidationError("Número do candidato não pode ser zero.")
        return value

class ApitidaoEleitorSerializer(serializers.ModelSerializer):
        eleitor_nome = serializers.CharField(source='eleitor.nome', read_only=True)
        eleicao_titulo = serializers.CharField(source='eleicao.titulo', read_only=True)

        class Meta:
            model = AptidaoEleitor
            fields = "__all__"

class RegistroVotacaoSerializer(serializers.ModelSerializer):
    
    eleitor_nome = serializers.CharField(source='eleitor.nome', read_only=True)
    eleicao_titulo = serializers.CharField(source='eleicao.titulo', read_only=True)

    class Meta:
        model = RegistroVotacao
        fields = "__all__"

class VotoSerializer(serializers.ModelSerializer):
    candidato_nome_urna = serializers.CharField(source='candidato.nome_urna', read_only=True, allow_null=True)
    em_branco_display = serializers.SerializerMethodField()

    class Meta:
        model = Voto
        fields = "__all__"
        extra_kwargs = {
            'comprovante_hash': {'write_only': True}
        }

    def get_em_branco_display(self, obj):
        return "BRANCO" if obj.em_branco else None

class VotacaoInputSerializer(serializers.Serializer):
    eleitor_id = serializers.IntegerField()
    eleicao_id = serializers.IntegerField()
    candidato_id = serializers.IntegerField(required=False)
    em_branco = serializers.BooleanField(default=False, required=False)

    def validate(self, data):
        if not Eleicao.objects.filter(id=data['eleicao_id'], status='aberta').exists():
            raise serializers.ValidationError("Eleição não existe ou não está aberta.")
        eleicao = Eleicao.objects.get(id=data['eleicao_id'])
        now = timezone.now()
        if not (eleicao.data_inicio <= now <= eleicao.data_fim):
            raise serializers.ValidationError("Eleição não está no período de votação.")
        if not AptidaoEleitor.objects.filter(eleitor_id=data['eleitor_id'], eleicao_id=data['eleicao_id']).exists():
            raise serializers.ValidationError("Eleitor não está apto para votar nesta eleição.")
        if RegistroVotacao.objects.filter(eleitor_id=data['eleitor_id'], eleicao_id=data['eleicao_id']).exists():
            raise serializers.ValidationError("Eleitor já votou nesta eleição.")
        if 'candidato_id' in data and data['candidato_id'] is not None:
            if not Candidato.objects.filter(id=data['candidato_id'], eleicao_id=data['eleicao_id']).exists():
                raise serializers.ValidationError("Candidato não pertence a esta eleição.")
        if ('candidato_id' in data and data['candidato_id'] is not None) and data.get('em_branco', False):
            raise serializers.ValidationError("Não pode votar em um candidato e em branco ao mesmo tempo.")
        if not ('candidato_id' in data and data['candidato_id'] is not None) and not data.get('em_branco', False):
            raise serializers.ValidationError("Deve votar em um candidato ou em branco.")
        return data
