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

    @action(detail=True, methods=['post'], url_path='cadastrar-aptos')
    def cadastrar_aptos(self, request, pk=None):
        eleicao = self.get_object()
        if eleicao.status != 'rascunho':
            return Response({'detail': 'Eleição deve estar em rascunho para cadastrar aptos'}, status=status.HTTP_400_BAD_REQUEST)

        eleitores_ids = request.data.get('eleitores_ids', [])
        if not isinstance(eleitores_ids, list) or not all(isinstance(i, int) for i in eleitores_ids):
            return Response({'detail': 'eleitores_ids deve ser uma lista de inteiros'}, status=status.HTTP_400_BAD_REQUEST)

        aptos_criados = 0
        for eleitor_id in eleitores_ids:
            try:
                AptidaoEleitor.objects.create(eleicao=eleicao, eleitor_id=eleitor_id, aptidao=True)
                aptos_criados += 1
            except IntegrityError:
                continue

        return Response({'total_cadastrados': aptos_criados}, status=status.HTTP_201_CREATED)


    @action(detail=True, methods=['get'], url_path='votantes')
    def votantes(self, request, pk=None):
        eleicao = self.get_object()
        compareceu = request.query_params.get('compareceu', 'true').lower() == 'true'
        if compareceu:
            registros = eleicao.registros_votacao.select_related('eleitor').all()
            data = [{
                'nome': r.eleitor.nome,
                'cpf': r.eleitor.cpf[-4:].rjust(len(r.eleitor.cpf), '*'),
                'data_hora': r.data_hora
            } for r in registros]
        else:
            aptos = eleicao.aptidoes.filter(aptidao=True).select_related('eleitor')
            compareceram_ids = eleicao.registros_votacao.values_list('eleitor_id', flat=True)
            data = [{
                'nome': a.eleitor.nome,
                'cpf': a.eleitor.cpf[-4:].rjust(len(a.eleitor.cpf), '*'),
            } for a in aptos if a.eleitor_id not in compareceram_ids]
        return Response(data)

    @action(detail=True, methods=['get'], url_path='apuracao')
    def apuracao(self, request, pk=None):
        eleicao = self.get_object()
        if eleicao.status not in ['encerrada', 'apurada']:
            return Response({'detail': 'Apuração só disponível para eleições encerradas ou apuradas'}, status=status.HTTP_403_FORBIDDEN)

        total_aptos = eleicao.aptidoes.filter(aptidao=True).count()
        total_votos_validos = eleicao.votos.filter(em_branco=False).count()
        total_votos_branco = eleicao.votos.filter(em_branco=True).count()
        total_abstencoes = total_aptos - eleicao.registros_votacao.count()

        candidatos_data = []
        for candidato in eleicao.candidatos.all():
            votos_candidato = eleicao.votos.filter(candidato=candidato, em_branco=False).count()
            percentual = (votos_candidato / total_votos_validos * 100) if total_votos_validos > 0 else 0
            candidatos_data.append({
                'id': candidato.id,
                'nome': candidato.nome,
                'votos': votos_candidato,
                'percentual': percentual
            })

        candidatos_data.sort(key=lambda x: x['votos'], reverse=True)
        max_votos = candidatos_data[0]['votos'] if candidatos_data else 0
        vencedores = [c for c in candidatos_data if c['votos'] == max_votos and max_votos > 0]

        if eleicao.status == 'encerrada':
            eleicao.status = 'apurada'
            eleicao.save()

        resultado = {
            'total_aptos': total_aptos,
            'total_votos_validos': total_votos_validos,
            'total_votos_branco': total_votos_branco,
            'total_abstencoes': total_abstencoes,
            'candidatos': candidatos_data,
            'vencedores': vencedores
        }
        return Response(resultado)

   
    @action(detail=True, methods=['post'], url_path='encerrar')
    def encerrar(self, request, pk=None):
        eleicao = self.get_object()
        if eleicao.status != 'aberta':
            return Response({'detail': 'Eleição deve estar aberta para ser encerrada'}, status=status.HTTP_400_BAD_REQUEST)

        eleicao.status = 'encerrada'
        eleicao.save()
        serializer = self.get_serializer(eleicao)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='abrir')
    def abrir(self, request, pk=None):
        eleicao = self.get_object()
        if eleicao.status != 'rascunho':
            return Response({'detail': 'Eleição deve estar em rascunho para ser aberta'}, status=status.HTTP_400_BAD_REQUEST)

        if eleicao.candidatos.count() < 2:
            return Response({'detail': 'Eleição deve ter pelo menos 2 candidatos'}, status=status.HTTP_400_BAD_REQUEST)

        if eleicao.aptidoes.filter(aptidao=True).count() < 1:
            return Response({'detail': 'Eleição deve ter pelo menos 1 eleitor apto'}, status=status.HTTP_400_BAD_REQUEST)

        eleicao.status = 'aberta'
        eleicao.save()
        serializer = self.get_serializer(eleicao)
        return Response(serializer.data)


    @action(detail=True, methods=['post'], url_path='votar')
    def votar(self, request, pk=None):
        eleicao = self.get_object()
        serializer = VotacaoInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        eleitor_id = serializer.validated_data['eleitor_id']
        candidato_id = serializer.validated_data.get('candidato_id')
        em_branco = serializer.validated_data.get('em_branco', False)

        try:
            registro = RegistroVotacao.objects.create(eleitor_id=eleitor_id, eleicao=eleicao)
        except IntegrityError:
            return Response({'detail': 'Eleitor já votou nesta eleição'}, status=status.HTTP_409_CONFLICT)

        token = secrets.token_urlsafe(32)

        voto = Voto.objects.create(
            eleicao=eleicao,
            candidato_id=candidato_id if not em_branco else None,
            em_branco=em_branco,
            comprovante_hash=token
        )
        
        # Gerar a imagem do QR Code (use qrcode + Pillow) codificando uma URL como /verificar-comprovante/?token=<TOKEN>
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        url_verificacao = request.build_absolute_uri(f'/eleicoes_api/verificar-comprovante/?token={token}')
        qr.add_data(url_verificacao)
        qr.make(fit=True)

        img = qr.make_image(fill='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        return Response({'token': token}, status=status.HTTP_201_CREATED)

    


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
    


@api_view(['GET'])
def verificar_comprovante(request):
    token = request.query_params.get('token')
    if not token:
        return Response({'valido': False, 'mensagem': 'Token é obrigatório'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        voto = Voto.objects.select_related('eleicao', 'candidato').get(comprovante_hash=token)
        resposta = {
            'eleicao': voto.eleicao.titulo,
            'candidato': voto.candidato.nome_urna if voto.candidato else 'BRANCO',
            'data_hora': voto.data_hora,
            'valido': True
        }
        return Response(resposta)
    except Voto.DoesNotExist:
        return Response({'valido': False, 'mensagem': 'Comprovante inválido'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def gerar_qr_code(request):
    token = request.query_params.get('token')
    if not token:
        return Response({'detail': 'Token é obrigatório'}, status=status.HTTP_400_BAD_REQUEST)

    url_verificacao = request.build_absolute_uri(f'/eleicoes_api/verificar-comprovante/?token={token}')
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url_verificacao)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return HttpResponse(buffer, content_type='image/png')