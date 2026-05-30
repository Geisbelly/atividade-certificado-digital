# Gerador de Certificado Digital Simulado — ICP-Brasil 🇧🇷

Atividade **educacional** que simula a geração de um certificado digital X.509
autoassinado, seguindo a estrutura usada na ICP-Brasil. Roda totalmente em **Docker**,
com **interface web** e uma aba didática completa.

> ⚠️ Certificado **autoassinado e simulado** — sem validade legal. Não substitui um
> certificado de Autoridade Certificadora credenciada na ICP-Brasil.

## Uso rápido (interface web)

```bash
# Construir a imagem e subir o servidor web
docker compose up -d --build web
```

Depois acesse no navegador: **http://localhost:5000**

- Aba **Gerar Certificado**: formulário, listagem dos certificados gerados e **modal** com todos os
  detalhes (informações, certificado decodificado, PEM e download).
- Aba **Explicação do Conteúdo**: material teórico completo (RSA, hash, X.509, ASN.1, TLS, ECC,
  pós-quântica, ICP-Brasil, glossário, referências…).

Os arquivos do último certificado também são salvos em `./saida/`:
- `certificate.pem` — certificado digital (público)
- `private_key.pem` — chave privada (guarde com segurança!)

Para parar o servidor:

```bash
docker compose down
```

## Modo linha de comando (opcional)

```bash
docker compose run --rm cli \
  --bits 4096 --estado "Minas Gerais" --cidade "Belo Horizonte" \
  --nome-comum "Maria Souza" --email "maria@exemplo.com.br" \
  --senha-chave "senhaForte"
```

## Documentação completa

Passo a passo detalhado e toda a fundamentação teórica em
**[PASSO_A_PASSO.md](PASSO_A_PASSO.md)**.
