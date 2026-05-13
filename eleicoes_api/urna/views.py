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