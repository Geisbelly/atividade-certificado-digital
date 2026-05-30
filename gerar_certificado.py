"""
Atividade: Geração de Certificados Digitais Simulados - ICP-Brasil
------------------------------------------------------------------
Este script simula, para fins EDUCACIONAIS, o processo de geração de um
certificado digital autoassinado no padrão X.509, em conformidade com a
estrutura de dados utilizada pela Infraestrutura de Chaves Públicas
Brasileira (ICP-Brasil).

ATENÇÃO: Este é um certificado AUTOASSINADO e SIMULADO. Ele NÃO possui
validade legal e NÃO substitui um certificado emitido por uma Autoridade
Certificadora (AC) credenciada na ICP-Brasil.

Bibliotecas utilizadas: cryptography
Execução recomendada: dentro do contêiner Docker (ver README.md).
"""

import argparse
import datetime
import ipaddress  # noqa: F401  (mantido caso queira adicionar SAN de IP)

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def gerar_par_de_chaves(tamanho_bits: int) -> rsa.RSAPrivateKey:
    """
    Tarefa 1 - Geração de um par de chaves RSA.

    :param tamanho_bits: Tamanho da chave em bits (>= 2048 recomendado).
    :return: Objeto da chave privada RSA (a chave pública é derivada dela).
    """
    if tamanho_bits < 2048:
        print(
            f"[AVISO] Tamanho de chave {tamanho_bits} bits é considerado fraco. "
            "Recomenda-se no mínimo 2048 bits."
        )

    chave_privada = rsa.generate_private_key(
        public_exponent=65537,   # valor padrão e seguro recomendado
        key_size=tamanho_bits,
    )
    print(f"[OK] Par de chaves RSA de {tamanho_bits} bits gerado com sucesso.")
    return chave_privada


def criar_certificado(chave_privada: rsa.RSAPrivateKey, dados: dict, dias_validade: int) -> x509.Certificate:
    """
    Tarefa 2 - Criação de um certificado X.509 autoassinado.

    :param chave_privada: Chave privada RSA usada para assinar o certificado.
    :param dados: Dicionário com os campos do titular (DN - Distinguished Name).
    :param dias_validade: Quantidade de dias de validade do certificado.
    :return: Objeto do certificado X.509 assinado.
    """
    # Distinguished Name (DN) do titular/emissor.
    # Em um certificado autoassinado, subject (titular) == issuer (emissor).
    nome = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, dados["pais"]),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, dados["estado"]),
        x509.NameAttribute(NameOID.LOCALITY_NAME, dados["cidade"]),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, dados["organizacao"]),
        x509.NameAttribute(NameOID.COMMON_NAME, dados["nome_comum"]),
    ])

    # Período de validade.
    inicio_validade = datetime.datetime.now(datetime.timezone.utc)
    fim_validade = inicio_validade + datetime.timedelta(days=dias_validade)

    construtor = (
        x509.CertificateBuilder()
        .subject_name(nome)                       # Titular
        .issuer_name(nome)                        # Emissor (mesmo, pois é autoassinado)
        .public_key(chave_privada.public_key())   # Chave pública do titular
        .serial_number(x509.random_serial_number())  # Número de série único
        .not_valid_before(inicio_validade)        # Início da validade (data atual)
        .not_valid_after(fim_validade)            # Término da validade (+1 ano por padrão)
        # Extensões típicas de um certificado:
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,   # não-repúdio
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectAlternativeName([x509.RFC822Name(dados["email"])]),
            critical=False,
        )
    )

    # Assinatura do certificado com a chave privada, usando SHA-256.
    certificado = construtor.sign(private_key=chave_privada, algorithm=hashes.SHA256())

    print("[OK] Certificado X.509 autoassinado criado e assinado (SHA-256).")
    print(f"     Início da validade : {inicio_validade.strftime('%d/%m/%Y %H:%M:%S UTC')}")
    print(f"     Término da validade: {fim_validade.strftime('%d/%m/%Y %H:%M:%S UTC')}")
    return certificado


def salvar_chave_privada(chave_privada: rsa.RSAPrivateKey, caminho: str, senha: str | None) -> None:
    """
    Tarefa 3 (parte 1) - Salva a chave privada em arquivo PEM.

    :param senha: Se informada, a chave é criptografada (boa prática de segurança).
    """
    if senha:
        algoritmo_cifra = serialization.BestAvailableEncryption(senha.encode("utf-8"))
    else:
        algoritmo_cifra = serialization.NoEncryption()

    pem = chave_privada.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=algoritmo_cifra,
    )
    with open(caminho, "wb") as f:
        f.write(pem)

    estado = "CRIPTOGRAFADA" if senha else "SEM senha (apenas para teste!)"
    print(f"[OK] Chave privada salva em '{caminho}' ({estado}).")


def salvar_certificado(certificado: x509.Certificate, caminho: str) -> None:
    """Tarefa 3 (parte 2) - Salva o certificado em arquivo PEM."""
    pem = certificado.public_bytes(serialization.Encoding.PEM)
    with open(caminho, "wb") as f:
        f.write(pem)
    print(f"[OK] Certificado salvo em '{caminho}'.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gerador de certificado digital X.509 simulado (ICP-Brasil) - educacional."
    )
    parser.add_argument("--bits", type=int, default=2048, help="Tamanho da chave RSA em bits (padrão: 2048).")
    parser.add_argument("--dias", type=int, default=365, help="Dias de validade (padrão: 365 = 1 ano).")
    parser.add_argument("--pais", default="BR", help="País (padrão: BR).")
    parser.add_argument("--estado", default="Sao Paulo", help="Estado/Província.")
    parser.add_argument("--cidade", default="Sao Paulo", help="Localidade/Cidade.")
    parser.add_argument("--organizacao", default="Organizacao Simulada LTDA", help="Nome da organização.")
    parser.add_argument("--nome-comum", default="Usuario de Teste", help="Nome comum (CN).")
    parser.add_argument("--email", default="usuario.teste@exemplo.com.br", help="E-mail do titular (SAN).")
    parser.add_argument("--senha-chave", default=None, help="Senha para proteger a chave privada (opcional).")
    parser.add_argument("--saida-chave", default="private_key.pem", help="Arquivo da chave privada.")
    parser.add_argument("--saida-cert", default="certificate.pem", help="Arquivo do certificado.")
    args = parser.parse_args()

    print("=" * 70)
    print("  GERAÇÃO DE CERTIFICADO DIGITAL SIMULADO - ICP-Brasil (educacional)")
    print("=" * 70)

    dados = {
        "pais": args.pais,
        "estado": args.estado,
        "cidade": args.cidade,
        "organizacao": args.organizacao,
        "nome_comum": args.nome_comum,
        "email": args.email,
    }

    # Tarefa 1
    chave_privada = gerar_par_de_chaves(args.bits)
    # Tarefa 2
    certificado = criar_certificado(chave_privada, dados, args.dias)
    # Tarefa 3
    salvar_chave_privada(chave_privada, args.saida_chave, args.senha_chave)
    salvar_certificado(certificado, args.saida_cert)

    print("=" * 70)
    print("  Concluído! Arquivos gerados:")
    print(f"   - {args.saida_chave}  (chave privada - GUARDE COM SEGURANÇA)")
    print(f"   - {args.saida_cert}  (certificado público)")
    print("=" * 70)


if __name__ == "__main__":
    main()
