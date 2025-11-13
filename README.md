# Rinha de Backend 2025 - Template FastAPI (Renato) — README

Este repositório contém um template didático para a Rinha de Backend 2025.
Objetivos:
- Permitir estudo do fluxo completo: health-check cacheado, escolha de processor, retries e persistência.
- Fornecer infra mínima com duas instâncias + nginx.
- Fácil de adaptar/otimizar para competição.

## Arquivos principais
- `app/` - código FastAPI (main, db, utils)
- `Dockerfile` - imagem do serviço
- `docker-compose.yml` - 2 instâncias + nginx (usa network externa `payment-processor`)
- `nginx.conf` - proxy para balancear entre api1 e api2
- `info.json` - metadata para submissão
- `requirements.txt` - dependências

## Como rodar localmente (passo a passo)

### 1) Clonar repositório dos Payment Processors oficiais
> Os Payment Processors precisam estar rodando para criar a rede e endpoints.

git clone https://github.com/zanfranceschi/rinha-de-backend-2025.git payment_processors
cd payment_processors
# suba os processors (veja instruções do repositório oficial)
docker compose up -d payment-processor-default payment-processor-fallback
Isto deve criar a rede payment-processor e expor:

http://localhost:8001 -> payment-processor-default

http://localhost:8002 -> payment-processor-fallback

2) Voltar para este projeto

cd ../rinha-backend-2025-renato
3) Build e run (modo desenvolvimento)

# build das imagens
docker compose build

# subir serviços (nginx + 2 apis)
docker compose up -d
Os endpoints estarão acessíveis via http://localhost:9999 (através do nginx):

POST http://localhost:9999/payments

json
{
  "correlationId": "uuid",
  "amount": 19.90
}
GET http://localhost:9999/payments-summary

4) Testes de carga (exemplo com hey ou k6)
Exemplo simples com hey:


hey -n 1000 -c 50 -m POST -H "Content-Type: application/json" -d '{"correlationId":"11111111-1111-1111-1111-111111111111","amount":10.0}' http://localhost:9999/payments
Para medir p99 use k6 ou outra ferramenta que gere relatórios de percentis.

Arquitetura e decisões de design (explicação)
Health check cacheado: para respeitar limite de 1 chamada a cada 5s. TTL definido em HEALTH_TTL=4.0 (configurável via env).

Escolha do processor: prioriza default se não estiver com failing=true. Caso contrário usa fallback.

Retries simples: se o primeiro processor responder com não-2xx ou lançar exceção, tentamos o outro.

Persistência: SQLite (/data/payments.db) gravando todas as tentativas para permitir auditoria e summary.

Balanceamento: nginx em frente a duas instâncias api1 e api2 para cumprir exigência de múltiplas instâncias.

Pontos de melhoria (para buscar vantagem na Rinha)
Implementar circuit-breaker (ex: usar tokens para abrir/fechar circuitos por processor).

Fazer seleção baseada em custo+latência (calcula lucro esperado vs risco).

Usar filas assíncronas para desacoplar recebimento do processamento e aumentar throughput.

Compactar chamadas de health-check com métricas de latência e histórico (ex: usar EWMA).

Otimizar p99: reduzir overhead do HTTP server (usar uvicorn workers, tune do Python), reduzir lock contention, mover summary para Redis para leituras rápidas.

Observações finais
Antes da submissão oficial, verifique os limites de CPU/memória no docker-compose.yml conforme regras da Rinha.

O repositório de submissão NÃO deve incluir código fonte (ver regras) — mas este template é para estudo e desenvolvimento local. Para submissão oficial, siga as instruções do enunciado.

Boa sorte — quer que eu:

Gere o repositório git com estes arquivos e o README pronto (conteúdo que você pode copiar),

Ou que eu gere um docker-compose-arm64.yml adicional?


---

# Observações finais (importante para você estudar e adaptar)
- O código acima é um **ponto de partida didático**. Ele inclui:
  - health-check cache (TTL 4s) para **não violar** 1 chamada/5s,
  - persistência simples para `payments-summary`,
  - retries básicos e gravação de tentativas para auditoria.
- Para competir bem na Rinha você precisa:
  - reduzir p99 (profundamente otimizar I/O, reduzir overhead, usar workers/uvloop),
  - otimizar lógica de decisão (escolher processor com menor custo sem incorrer em inconsistências),
  - testar localmente com carga e ajustar CPU/memória do `docker-compose`.

---


