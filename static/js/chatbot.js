// static/js/chatbot.js
document.addEventListener('DOMContentLoaded', () => {
    const calculateBtn = document.getElementById('calculate-btn');
    const apiFeedback = document.getElementById('api-feedback');
    const chatInput = document.getElementById('chat-input');
    const chatInputGroup = document.querySelector('.input-group');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const chatWindow = document.getElementById('chat-window');

    // --- Estado do Chat (NOVAS PERGUNTAS) ---
    let currentQuestionIndex = 0;
    const qualitativeAnswers = ["BAIXO", "NÃO CONSIGO AVALIAR", "MÉDIO", "ALTO", "ELEVADO"];

    const questions = [
        // --- Bloco 1: Financeiro ---
        { id: 'faturamento_mensal', text: "Qual foi o faturamento bruto aproximado no último mês?", type: 'number_positive' },
        { id: 'gastos_variaveis', text: "Quais são os seus custos variáveis mensais aproximados?", type: 'number_non_negative' },
        { id: 'gastos_fixos', text: "Quais são os seus custos fixos mensais aproximados?", type: 'number_non_negative' },
        { id: 'num_vendas', text: "Qual foi o número total de vendas no último mês?", type: 'integer_positive' },
        { id: 'num_prospeccoes', text: "Quantos clientes (leads) foram prospectados no último mês?", type: 'integer_positive' },
        { id: 'setor_atuacao', text: "Em qual setor principal sua empresa atua? (Ex: Varejo, Tecnologia, Saúde)", type: 'text' },
        
        // --- Bloco 2: Autoavaliação (18 perguntas) ---
        // Peso 1
        { id: 'visao_pessoas', text: "Como você avalia a Visão das pessoas sobre a ideia/ modelo de negócio?", type: 'qualitative' },
        { id: 'nivel_validacao', text: "Como você avalia o Nível das pesquisas de Validação?", type: 'qualitative' },
        { id: 'nivel_equipe', text: "Como você avalia o Nível da equipe?", type: 'qualitative' },
        { id: 'potencial_network', text: "Como você avalia o Potencial do Network da Equipe?", type: 'qualitative' },
        // Peso 2
        { id: 'diferencial_modelo', text: "Como você avalia o Diferencial do modelo de negócio em relação aos concorrentes?", type: 'qualitative' },
        { id: 'possibilidade_escala', text: "Como você avalia a Possibilidade de escala?", type: 'qualitative' },
        { id: 'pmf', text: "Como você avalia o Product Market Fit (PMF)?", type: 'qualitative' },
        { id: 'potencial_alcance', text: "Como você avalia o Potencial de Alcance do Público (Crescimento do Mercado)?", type: 'qualitative' },
        { id: 'nivel_parcerias', text: "Como você avalia o Nível de Parcerias já constituídas?", type: 'qualitative' },
        { id: 'estagio_modelo', text: "Como você avalia o Estágio do modelo de negócio?", type: 'qualitative' },
        { id: 'estagio_prototipo', text: "Como você avalia o Estágio do protótipo?", type: 'qualitative' },
        { id: 'nivel_analise_financeira', text: "Como você avalia o Nível do levantamento/ análise financeira?", type: 'qualitative' },
        { id: 'estagio_comercializacao', text: "Como você avalia o Estágio de comercialização do modelo de negócio?", type: 'qualitative' },
        { id: 'nivel_faturamento', text: "Como você avalia o Nível de faturamento do modelo de negócio?", type: 'qualitative' },
        { id: 'nivel_lucro', text: "Como você avalia o Nível de lucro do modelo de negócio?", type: 'qualitative' },
        // Peso -2
        { id: 'possibilidade_copia', text: "Como você avalia a Possibilidade de ser copiado?", type: 'qualitative' },
        { id: 'potencial_mercado_barreiras', text: "Como você avalia o Potencial de Mercado (barreiras legais/ políticas/ econômicas)?", type: 'qualitative' },
        { id: 'potencial_internacionalizacao', text: "Como você avalia o Potencial de Internacionalização (barreiras culturais)?", type: 'qualitative' }
    ];
    
    let chatInputs = {}; // Respostas serão armazenadas aqui

    // --- Funções Auxiliares ---
    function addChatMessage(message, type = 'bot') {
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message ${type}`;
        msgDiv.textContent = message;
        chatWindow.appendChild(msgDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight; // Auto-scroll
    }

    function disableInput() {
        chatInput.disabled = true;
        chatSendBtn.disabled = true;
        chatInputGroup.style.display = 'none'; // Esconde o input
    }

    function enableInput(placeholder = "Digite sua resposta aqui...") {
        chatInput.disabled = false;
        chatSendBtn.disabled = false;
        chatInput.placeholder = placeholder;
        chatInputGroup.style.display = 'flex'; // Mostra o input
        chatInput.focus();
    }

    // Função para limpar botões de resposta anteriores
    function clearResponseButtons() {
        const existingButtons = chatWindow.querySelectorAll('.response-buttons');
        existingButtons.forEach(btnGroup => btnGroup.remove());
    }

    // Função para criar os 5 botões de avaliação
    function createQualitativeButtons() {
        clearResponseButtons(); // Remove botões antigos

        const buttonGroup = document.createElement('div');
        buttonGroup.className = 'response-buttons d-flex flex-wrap justify-content-center p-2';
        
        qualitativeAnswers.forEach(answer => {
            const button = document.createElement('button');
            button.className = 'btn btn-outline-primary m-1';
            button.textContent = answer;
            button.onclick = () => handleQualitativeAnswer(answer);
            buttonGroup.appendChild(button);
        });

        chatWindow.appendChild(buttonGroup);
        chatWindow.scrollTop = chatWindow.scrollHeight; // Auto-scroll
    }

    function askQuestion() {
        clearResponseButtons(); // Limpa botões da pergunta anterior

        if (currentQuestionIndex < questions.length) {
            const question = questions[currentQuestionIndex];
            addChatMessage(question.text);

            if (question.type === 'qualitative') {
                disableInput(); // Esconde o input de texto
                createQualitativeButtons(); // Mostra os 5 botões
            } else {
                enableInput(); // Mostra o input de texto
            }
        } else {
            // Fim das perguntas
            addChatMessage("Excelente! Coletei todos os dados. Agora, por favor, clique no botão \"Calcular Valuation\" ao lado.");
            disableInput();
            calculateBtn.disabled = false; // Ativa o botão de calcular
        }
    }

    // --- Funções de Validação ---
    function validateInput(input, type) {
        let value = input.trim();
        let num;

        switch (type) {
            case 'number': // Qualquer número
                num = parseFloat(value.replace(',', '.'));
                return !isNaN(num) ? num : { error: "Por favor, insira um valor numérico válido." };
            case 'number_positive': // Número > 0
                num = parseFloat(value.replace(',', '.'));
                return !isNaN(num) && num > 0 ? num : { error: "Por favor, insira um número positivo maior que zero." };
            case 'number_non_negative': // Número >= 0
                num = parseFloat(value.replace(',', '.'));
                return !isNaN(num) && num >= 0 ? num : { error: "Por favor, insira um número válido (zero ou maior)." };
            case 'integer_positive': // Inteiro > 0
                if (!/^\d+$/.test(value) || parseInt(value, 10) <= 0) {
                    return { error: "Por favor, insira um número inteiro maior que zero." };
                }
                return parseInt(value, 10);
            case 'text': // Texto não vazio
                return value.length > 0 ? value : { error: "Esta resposta não pode ficar em branco." };
            default:
                return value; // Sem validação específica
        }
    }

    // --- Lógica Principal do Chat ---

    // 1. Para respostas de texto (Financeiras)
    function handleChatSend() {
        const message = chatInput.value;
        if (message.trim() === '' || currentQuestionIndex >= questions.length) return;

        const currentQuestion = questions[currentQuestionIndex];
        if (currentQuestion.type === 'qualitative') return; 

        addChatMessage(message, 'user');
        chatInput.value = '';

        const validationResult = validateInput(message, currentQuestion.type);

        if (validationResult && typeof validationResult === 'object' && validationResult.error) {
            addChatMessage(validationResult.error);
            enableInput();
        } else {
            chatInputs[currentQuestion.id] = validationResult;
            currentQuestionIndex++;
            disableInput();
            setTimeout(askQuestion, 500);
        }
    }

    // 2. Para respostas de botão (Qualitativas)
    function handleQualitativeAnswer(answer) {
        addChatMessage(answer, 'user');
        
        const currentQuestion = questions[currentQuestionIndex];
        chatInputs[currentQuestion.id] = answer;
        
        currentQuestionIndex++;
        disableInput();
        setTimeout(askQuestion, 500);
    }

    chatSendBtn.addEventListener('click', handleChatSend);
    chatInput.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') {
            handleChatSend();
        }
    });

    // --- Lógica da API (COM A MUDANÇA) ---
    calculateBtn.addEventListener('click', () => {
        calculateBtn.disabled = true;
        calculateBtn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processando...`;
        apiFeedback.innerHTML = '<div class="alert alert-info small">Iniciando análise... Isso pode levar algum tempo.</div>';

        fetch('/chatbot/api/calculate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // 'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ inputs: chatInputs })
        })
        .then(response => response.json().then(data => ({ status: response.status, body: data })))
        .then(({ status, body }) => {
            if (status === 200) {
                apiFeedback.innerHTML = `
                    <div class="alert alert-success alert-dismissible fade show" role="alert">
                        <strong>Sucesso!</strong> ${body.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>`;
                
                // --- MUDANÇA AQUI ---
                // Não reiniciamos as perguntas. Mostramos os botões.
                chatWindow.innerHTML = ''; // Limpa as perguntas
                addChatMessage("Sua análise foi iniciada! Você pode acompanhar o progresso no seu histórico ou iniciar uma nova simulação.");
                
                // Cria o grupo de botões
                const buttonGroup = document.createElement('div');
                buttonGroup.className = 'response-buttons d-flex flex-wrap justify-content-center p-2';

                // Botão 1: Ir para o Histórico
                const historyBtn = document.createElement('a');
                historyBtn.href = '/reports/history/'; // URL Hardcoded
                historyBtn.className = 'btn btn-primary m-1';
                historyBtn.innerHTML = '<i class="bi bi-clock-history me-2"></i> Ir para o Histórico';
                buttonGroup.appendChild(historyBtn);

                // Botão 2: Nova Simulação
                const newSimBtn = document.createElement('button');
                newSimBtn.className = 'btn btn-outline-secondary m-1';
                newSimBtn.innerHTML = '<i class="bi bi-plus-circle me-2"></i> Iniciar Nova Simulação';
                newSimBtn.onclick = () => {
                    // Reseta tudo para começar de novo
                    Object.keys(chatInputs).forEach(key => { delete chatInputs[key]; });
                    currentQuestionIndex = 0;
                    chatWindow.innerHTML = '';
                    apiFeedback.innerHTML = ''; // Limpa o alerta de sucesso
                    calculateBtn.disabled = true;
                    calculateBtn.innerHTML = '<i class="bi bi-calculator-fill me-2"></i> Calcular Valuation';
                    askQuestion(); // Faz a primeira pergunta
                };
                buttonGroup.appendChild(newSimBtn);

                chatWindow.appendChild(buttonGroup);
                chatWindow.scrollTop = chatWindow.scrollHeight;
                // --- FIM DA MUDANÇA ---

            } else {
                throw new Error(body.message || `Erro ${status}`);
            }
        })
        .catch(error => {
            console.error('Erro na API:', error);
            apiFeedback.innerHTML = `
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    <strong>Erro:</strong> ${error.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>`;
            calculateBtn.disabled = false;
            calculateBtn.innerHTML = '<i class="bi bi-x-octagon-fill me-2"></i> Falha! Tentar Calcular Novamente';
        });
    });
    
    // Função para pegar Cookie (se necessário)
    function getCookie(name) { /* ... (código da função getCookie) ... */ }

    // --- Iniciar o Chat ---
    calculateBtn.disabled = true;
    askQuestion(); // Faz a primeira pergunta

});