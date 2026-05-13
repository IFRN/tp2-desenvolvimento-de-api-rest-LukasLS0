from django.db import models
from django.core.exceptions import ValidationError

class Eleitor(models.Model):
    nome = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    cpf = models.CharField(max_length=14, unique=True) # 000.000.000-00
    data_nascimento = models.DateField()
    ativo = models.BooleanField(default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome
    
class Eleicao(models.Model):
    TIPOS_CHOICES = (
        ("estudantil", "Estudantil"),
        ("sindical", "Sindical"),
        ("associacao", "Associação"),
        ("condominio", "Condomínio"),
        ("conselho", "Conselho"),
        ("outros", "Outros")
    )

    STATUS_CHOICES = (
        ("rascunho", "Rascunho"),
        ("aberta", "Aberta"),
        ("encerrada", "Encerrada"),
        ("apurada", "Apurada")
    )
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    tipo = models.CharField(choices=TIPOS_CHOICES, default="rascunho") 
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    status = models.CharField(choices=STATUS_CHOICES, default="rascunho")
    permite_branco = models.BooleanField(default=True)
    criada_por = models.ForeignKey(Eleitor, on_delete=models.PROTECT, related_name="eleicoes_criadas")

    def clean(self):
        
        if self.data_fim <= self.data_inicio:
            raise ValidationError("A data de fim deve ser posterior à data de início.")
        if self.status == "aberta" and self._state.adding:
            if self.status != "rascunho":
                raise ValidationError("A eleição deve estar em rascunho para ser aberta.")
        if self.status == "encerrada" and self._state.adding:
            if self.status != "aberta":
                raise ValidationError("A eleição deve estar aberta para ser encerrada.")
        if self.status == "apurada" and self._state.adding:
            if self.status != "encerrada":
                raise ValidationError("A eleição deve estar encerrada para ser apurada.")

class Candidato(models.Model):
    eleicao = models.ForeignKey(Eleicao, on_delete=models.CASCADE, related_name="candidatos")
    numero = models.PositiveIntegerField()
    nome = models.CharField(max_length=150)
    nome_urna = models.CharField(max_length=50)
    partido_ou_chapa = models.CharField(max_length=100, blank=True)
    proposta = models.TextField(blank=True)
    foto = models.URLField(blank=True)

    class Meta:
        unique_together = ("eleicao", "numero")
    
class AptidaoEleitor(models.Model):
    eleitor = models.ForeignKey(Eleitor, on_delete=models.PROTECT, related_name="aptidoes")
    eleicao = models.ForeignKey(Eleicao, on_delete=models.CASCADE, related_name="aptos")
    data_inclusao = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("eleitor", "eleicao")

class RegistroVotacao(models.Model):
    eleitor = models.ForeignKey(Eleitor, on_delete=models.PROTECT, related_name="registros_votacao")
    eleicao = models.ForeignKey(Eleicao, on_delete=models.PROTECT, related_name="registros_votacao")
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("eleitor", "eleicao")

class Voto(models.Model):
    eleicao = models.ForeignKey(Eleicao, on_delete=models.PROTECT, related_name="votos")
    candidato = models.ForeignKey(Candidato, on_delete=models.PROTECT, related_name="votos", null=True, blank=True)
    em_branco = models.BooleanField(default=False)
    data_hora = models.DateTimeField(auto_now_add=True)
    comprovante_hash = models.CharField(max_length=64, unique=True) #SHA256 DO TOKEM ENTREGUE AO ELEITOR

    def clean(self):
        if self.em_branco and self.candidato is not None:
            raise ValidationError("Voto em branco não pode ter candidato.")
        if not self.em_branco and self.candidato is None:
            raise ValidationError("Voto não pode ser em branco sem candidato.")
