# WA-MediaSorter — Organizador Inteligente de Imagens do WhatsApp

<!-- Aplicação local para Windows desenvolvida em **Python** e **FastAPI**, com interface web leve em português, que identifica imagens de interesse em grupos do WhatsApp, aplica regras configuráveis pelo usuário e salva as imagens aprovadas em um diretório escolhido.

---

## 1. Visão Geral da Arquitetura

O sistema adota uma arquitetura modular, desacoplada e 100% executada no computador do usuário (localhost: `127.0.0.1`), com custo de infraestrutura de **R$ 0/mês** e total privacidade:

```
WA-MediaSorter/
├── app/
│   ├── main.py                     # Inicialização do servidor FastAPI e roteamento estático
│   ├── config.py                   # Configurações globais, caminhos e formatos permitidos
│   ├── api/                        # Endpoints REST da aplicação
│   │   ├── dashboard.py            # Resumo do painel inicial e estatísticas
│   │   ├── rules.py                # CRUD e alternância (toggle) de regras
│   │   ├── destination.py          # Configuração e validação de permissões de pastas
│   │   ├── whatsapp.py             # Status, conexão e grupos do WhatsApp
│   │   └── processing.py           # Prévia, processamento em segundo plano e amostras
│   ├── models/                     # Modelos de dados Pydantic
│   │   ├── rule.py                 # Definições de regras, critérios e decisões
│   │   ├── item.py                 # Modelos de mídias e itens processados
│   │   └── history.py              # Registros de histórico de execuções
│   ├── services/                   # Lógica de negócio e orquestração
│   │   ├── image_analyzer.py       # Validação de integridade, assinaturas e análise visual
│   │   ├── image_downloader.py     # Salvamento, prevenção de duplicatas (SHA-256) e conflitos
│   │   ├── rule_engine.py          # Avaliação determinística de critérios (AND/OR, thresholds)
│   │   └── processing_service.py   # Orquestrador não-bloqueante com suporte a cancelamento
│   ├── integrations/whatsapp/      # Módulo isolado de integração
│   │   ├── base.py                 # Interface abstrata e estados de conexão
│   │   └── client.py               # Cliente WhatsApp Web e provedor de amostras locais
│   └── repositories/               # Persistência local
│       ├── rule_repository.py      # Persistência JSON de regras e destino
│       └── history_repository.py   # Histórico e hashes de deduplicação em SQLite
├── frontend/                       # Interface web leve e responsiva
│   ├── index.html                  # Painel inicial, abas, modais e grade de resultados
│   ├── css/style.css               # Estilos modernos em tema escuro sem dependências pesadas
│   └── js/app.js                   # Lógica de interação, polling de status e chamadas API
├── sample_images/                  # Imagens e arquivos de teste para demonstração imediata
├── downloads/                      # Destino padrão inicial das imagens salvas
├── tests/                          # Suíte completa de testes automatizados com pytest
├── requirements.txt                # Dependências fixadas e compatíveis
├── run.bat                         # Script Windows para inicialização em 1 clique
├── run_tests.bat                   # Script Windows para rodar testes automatizados
└── README.md                       # Documentação completa
```

---

## 2. Requisitos e Pré-requisitos

- **Sistema Operacional:** Windows 10 ou Windows 11.
- **Python:** Versão 3.10 ou 3.11 recomendada (instalada pelo usuário conforme preferência).
- **Navegador Web:** Qualquer navegador moderno (Edge, Chrome, Firefox, Brave).

---

## 3. Instalação Passo a Passo

Para quem está aprendendo Python, siga os passos abaixo no terminal (PowerShell ou Prompt de Comando) dentro da pasta do projeto:

### Passo 1: Criar o Ambiente Virtual
O ambiente virtual isola os pacotes deste projeto para não misturar com o restante do computador:
```powershell
python -m venv .venv
```

### Passo 2: Ativar o Ambiente Virtual
```powershell
# No PowerShell:
.\.venv\Scripts\Activate.ps1

# Ou no Prompt de Comando (cmd):
.venv\Scripts\activate.bat
```

### Passo 3: Instalar as Dependências
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Executando a Aplicação

### Forma Mais Simples (Script Windows .bat):
Basta dar um duplo clique no arquivo:
```
run.bat
```
O script ativará o ambiente virtual, iniciará o servidor FastAPI e abrirá seu navegador automaticamente no endereço local:
**http://127.0.0.1:8000**

### Forma Manual (Linha de Comando):
Com o ambiente `.venv` ativado:
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Para encerrar a aplicação a qualquer momento, pressione **`CTRL + C`** no terminal.

---

## 5. Como Usar o Sistema

1. **Painel Inicial:** Apresenta o status em tempo real da aplicação, conexão, destino, regras ativas e métricas da sessão atual.
2. **Configuração de Regras:**
   - Crie novas regras definindo nome, tipo de critério (texto, logotipo de referência ou objeto), operador (`AND` ou `OR`) e limite mínimo de confiança (ex: 50%).
   - Ative, desative ou edite regras a qualquer momento sem alterar código Python.
3. **Pasta de Destino:**
   - Escolha o diretório local onde as imagens aprovadas devem ser salvas.
   - O sistema valida automaticamente as permissões de gravação antes do processamento.
4. **Prévia e Processamento:**
   - **Modo Amostra Local:** Permite testar o motor de regras e a gravação imediatamente utilizando imagens de exemplo contidas em `sample_images/` (ou adicionando novas imagens pelo botão "Adicionar Imagem de Teste").
   - **Modo WhatsApp:** Permite processar imagens recebidas nos grupos selecionados do WhatsApp quando conectado.
   - **Prévia:** Clique em "Visualizar Prévia" para inspecionar miniaturas, critérios correspondidos e o motivo da decisão antes de salvar.
   - **Processamento:** Clique em "Iniciar Processamento". A execução ocorre em segundo plano com barra de progresso e botão de "Cancelar" instantâneo.
5. **Histórico:** Consulte as execuções anteriores registradas no banco local SQLite com data, grupo, quantidade de imagens analisadas, aprovadas e salvas.

---

## 6. Políticas de Segurança e Salvamento de Arquivos

- **Prevenção de Duplicatas (Hash SHA-256):** O sistema calcula o hash criptográfico do conteúdo das imagens. Arquivos idênticos já salvos anteriormente não são duplicados.
- **Resolução de Conflitos de Nome:** Arquivos existentes no destino **nunca** são sobrescritos silenciosamente. Se `foto.jpg` já existir, o novo arquivo será salvo como `foto_1.jpg`, `foto_2.jpg`, etc.
- **Validação de Conteúdo Real:** O sistema não confia apenas na extensão (`.jpg`, `.png`). Ele verifica os *magic bytes* e integridade com a biblioteca Pillow, rejeitando vídeos (MP4, MKV), áudios, PDFs, compactados e arquivos corrompidos.
- **Isolamento e Segurança Local:**
  - O servidor escuta estritamente em `127.0.0.1`.
  - Tentativas de *path traversal* (manipulação de caminhos para fora da pasta autorizada) são sanitizadas e bloqueadas.
  - Imagens originais nunca são apagadas ou modificadas.

---

## 7. Análise Técnica e Estado Real da Integração com WhatsApp

Conforme determinado pelos requisitos do projeto:

1. **Inviabilidade de APIs Pagas:**
   - A API oficial do *WhatsApp Business (Meta Cloud API)* exige cadastro de empresa (Meta Business Manager), webhook público na nuvem, cobrança por mensagem/conversa iniciada e **não permite acesso irrestrito a grupos pessoais pré-existentes** de um usuário comum. Portanto, viola o custo R$ 0/mês e o escopo de uso pessoal local.
2. **Alternativa Gratuita e Viável (WhatsApp Web Local):**
   - A alternativa técnica gratuita no Windows é a automação local do WhatsApp Web via navegador headless (ex: Playwright com Chromium).
   - A autenticação é realizada diretamente pelo próprio usuário escaneando o QR Code pelo aplicativo oficial em seu celular (*Aparelhos Conectados*).
   - O sistema foi desenvolvido com uma arquitetura modular isolada (`app/integrations/whatsapp/`), separando a interface e o motor de regras de bibliotecas específicas.
3. **Estado Atual e Transparência:**
   - O sistema detecta dinamicamente a presença do driver de navegador local. Caso o pacote `playwright` e os binários do Chromium não estejam presentes no ambiente Python, o sistema informa claramente o status **"Driver Indisponível"** e não simula conexões falsas nem inventa grupos fictícios.
   - Para permitir testes completos e auditoria imediata de todas as funcionalidades de negócio (regras, persistência, prévia, deduplicação e salvamento), o sistema inclui o **Modo Amostra Local**, identificado de forma 100% transparente na interface.

---

## 8. Execução dos Testes Automatizados

A suíte de testes cobre todas as regras de negócio e operações locais exigidas. Para executar:

### Opção 1: Via Script .bat
Dê um duplo clique em `run_tests.bat`.

### Opção 2: Linha de Comando
Com o ambiente `.venv` ativado:
```powershell
pytest tests/ -v
```

### Cenários Testados:
1. `test_text_criterion_met_and_not_met`: Critério textual aprovado com palavras-chave e rejeitado sem elas.
2. `test_logical_operator_and_all_met`: Avaliação de múltiplos critérios com operador AND quando todos são atendidos.
3. `test_logical_operator_and_partial_fail`: Operador AND rejeitando quando um critério falha.
4. `test_logical_operator_or`: Operador OR aprovando quando ao menos um critério é atendido.
5. `test_deactivated_rule_not_evaluated`: Regra desativada ignorada na avaliação.
6. `test_confidence_threshold_rejection`: Limite de confiança mínima rejeitando pontuações inferiores.
7. `test_unavailable_criterion_never_auto_passed`: Critério indisponível **nunca** considerado automaticamente aprovado.
8. `test_valid_image_saving`: Imagem íntegra salva com sucesso.
9. `test_reject_corrupted_or_invalid_file`: Arquivo corrompido rejeitado.
10. `test_reject_video_and_documents`: Rejeição explícita de vídeos (MP4) e documentos (PDF).
11. `test_duplicate_detection_by_hash`: Detecção de duplicatas por hash SHA-256 evitando re-gravação.
12. `test_filename_conflict_resolution`: Resolução de colisão de nomes com sufixos `_1`, `_2` sem sobrescrita.
13. `test_invalid_destination_validation`: Tratamento de caminhos inválidos ou vazios.
14. `test_rule_repository_crud_and_persistence`: Persistência de regras em arquivo JSON após reinício.
15. `test_history_repository_sqlite`: Registro e consulta de execuções no banco SQLite.
16. `test_preview_does_not_save_files`: Garantia de que a prévia não grava arquivos no destino.
17. `test_processing_cancellation`: Cancelamento imediato de processamento em andamento.
18. `test_api_*`: Testes de integração em todos os endpoints REST do FastAPI.

---

## 9. Solução de Problemas Comuns

| Problema | Causa Provável | Solução |
| :--- | :--- | :--- |
| **`python: command not found`** | Python não instalado ou não adicionado ao PATH | Instale o Python (3.10+) marcando a opção *"Add python.exe to PATH"*. |
| **`Script execution is disabled` (PowerShell)** | Política de execução de scripts do Windows restrita | Execute `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` ou utilize o Prompt de Comando (cmd). |


-->

-->
| **"Sem permissão de gravação na pasta"** | Pasta de destino protegida pelo sistema operacional | Escolha uma pasta do seu usuário, como `C:\Users\SeuUsuario\Downloads` ou `Imagens`. |
| **Porta 8000 já em uso** | Outro aplicativo local está utilizando a porta 8000 | Altere a porta no arquivo `app/config.py` ou encerre o processo conflitante. |
| **Driver do WhatsApp indisponível** | Pacote `playwright` não instalado no ambiente | Execute `pip install playwright` seguido de `playwright install chromium`. |
