/**
 * Rimuove un task specifico dalla lista
 * @param {number} taskGroupIndex - Indice del gruppo di task
 * @param {number} taskIndex - Indice del task nel gruppo
 */
function removeTask(taskGroupIndex, taskIndex) {
    if (confirm('Sei sicuro di voler rimuovere questo task?')) {
        fetch(`/task/remove-task/${taskGroupIndex}/${taskIndex}`, {
            method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Rimuovi l'elemento dal DOM
                const taskElement = document.querySelector(`#task-${taskGroupIndex}-${taskIndex}`);
                taskElement.remove();
                
                // Se non ci sono più task nel gruppo, rimuovi l'intero gruppo
                const taskGroup = document.querySelector(`#task-group-${taskGroupIndex}`);
                if (!taskGroup.querySelector('.task-item')) {
                    taskGroup.remove();
                }
                
                // Aggiorna il contatore dei task
                updateTaskCounter(taskGroupIndex);
            }
        });
    }
}

/**
 * Aggiunge un task personalizzato al gruppo specificato
 * @param {Event} event - Evento del form submit
 * @param {number} groupIndex - Indice del gruppo di task
 */
function addCustomTask(event, groupIndex) {
    event.preventDefault();
    
    const form = event.target;
    const input = form.querySelector('.new-task-input');
    const taskText = input.value.trim();
    
    if (!taskText) return;
    
    fetch('/task/add-custom-task', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            groupIndex: groupIndex,
            taskText: taskText
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Aggiorna la UI per mostrare il nuovo task
            const taskList = document.querySelector(`#task-group-${groupIndex} .task-list`);
            const newTaskElement = document.createElement('div');
            newTaskElement.id = `task-${groupIndex}-${data.taskIndex}`;
            newTaskElement.className = 'task-item';
            newTaskElement.innerHTML = `
                <div class="task-content">
                    <span class="completion-icon">⭕</span>
                    <p>${taskText}</p>
                </div>
                <button class="remove-task" 
                        data-group-index="${groupIndex}" 
                        data-task-index="${data.taskIndex}"
                        onclick="removeTask(${groupIndex}, ${data.taskIndex})">
                    Rimuovi
                </button>
            `;
            taskList.appendChild(newTaskElement);
            
            // Reset del form
            input.value = '';
            
            // Aggiorna il contatore dei task
            updateTaskCounter(groupIndex);
        }
    });
}

/**
 * Aggiorna il contatore di task per un gruppo specifico
 * @param {number} groupIndex - Indice del gruppo di task
 */
function updateTaskCounter(groupIndex) {
    const taskGroup = document.querySelector(`#task-group-${groupIndex}`);
    const taskCount = taskGroup.querySelectorAll('.task-item').length;
    const counterElement = taskGroup.querySelector('.task-count');
    counterElement.textContent = `#${taskCount} tasks`;
}

/**
 * Mostra il feedback di caricamento e disabilita il pulsante al submit
 * @param {Event} event - Evento del form submit
 */
function showLoadingOnSubmit(event) {
    const form = event.currentTarget;
    const submitButtons = form.querySelectorAll('button[type="submit"]');
    
    // Disabilita tutti i pulsanti di submit nel form
    submitButtons.forEach(button => {
        button.disabled = true;
        
        // Salva il testo originale e mostra il testo di caricamento
        button.dataset.originalText = button.textContent;
        button.textContent = "Caricamento...";
        
        // Aggiungi la classe di caricamento
        button.classList.add('loading');
    });
    
    // Ritorna true per permettere l'invio del form
    return true;
}

/**
 * Inizializza gli event listeners per i form nella pagina
 */
function initFormListeners() {
    // Aggiungi event listener per il form di generazione task
    const mainForm = document.getElementById('main-form');
    if (mainForm) {
        mainForm.addEventListener('submit', showLoadingOnSubmit);
    }
    
    // Aggiungi event listener per il form delle domande
    const questionsForm = document.getElementById('questions-form');
    if (questionsForm) {
        questionsForm.addEventListener('submit', showLoadingOnSubmit);
    }
}

// Esegui l'inizializzazione quando il documento è pronto
document.addEventListener('DOMContentLoaded', initFormListeners);

/**
 * Avvia il processo di ricerca automatica per i task non completati
 * @param {number} groupIndex - Indice del gruppo di task
 */
function startResearch(groupIndex) {
    // Disabilitiamo il pulsante e cambiamo il testo
    const button = document.querySelector(`#task-group-${groupIndex} .research-btn`);
    button.disabled = true;
    button.textContent = "Ricerca in corso...";
    
    // Otteniamo l'ID della ricerca dal dataset del body
    const researchId = document.body.dataset.researchId || '';
    
    // Avviamo la ricerca con una chiamata AJAX
    fetch(`/research/${researchId}/start-research/${groupIndex}`, {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Iniziamo a controllare lo stato di avanzamento
            checkResearchProgress(researchId, groupIndex);
        } else {
            alert("Errore nell'avvio della ricerca: " + data.error);
            button.disabled = false;
            button.textContent = "Ricerca automatica";
        }
    })
    .catch(error => {
        console.error("Errore:", error);
        button.disabled = false;
        button.textContent = "Ricerca automatica";
    });
}

/**
 * Controlla lo stato di avanzamento della ricerca
 * @param {string} researchId - ID della ricerca
 * @param {number} groupIndex - Indice del gruppo di task
 */
function checkResearchProgress(researchId, groupIndex) {
    fetch(`/research/${researchId}/check-research-progress/${groupIndex}`)
    .then(response => response.json())
    .then(data => {
        if (data.completed) {
            // La ricerca è completata, ricarichiamo la pagina
            location.reload();
        } else if (data.in_progress) {
            // Aggiorniamo i task già completati
            data.completed_tasks.forEach(taskIndex => {
                const taskElement = document.querySelector(`#task-${groupIndex}-${taskIndex}`);
                if (taskElement) {
                    taskElement.classList.add('completed');
                    taskElement.querySelector('.completion-icon').innerHTML = '✅';
                }
            });
            
            // Evidenziamo il task in corso
            if (data.current_task_index !== null) {
                const currentTaskElement = document.querySelector(`#task-${groupIndex}-${data.current_task_index}`);
                if (currentTaskElement) {
                    currentTaskElement.classList.add('in-progress');
                }
            }
            
            // Controlliamo nuovamente tra 2 secondi
            setTimeout(() => checkResearchProgress(researchId, groupIndex), 2000);
        } else {
            // La ricerca è stata interrotta per qualche motivo
            const button = document.querySelector(`#task-group-${groupIndex} .research-btn`);
            button.disabled = false;
            button.textContent = "Ricerca automatica";
        }
    })
    .catch(error => {
        console.error("Errore nel controllo dello stato:", error);
        // Riproviamo dopo un po'
        setTimeout(() => checkResearchProgress(researchId, groupIndex), 5000);
    });
}

/**
 * Controlla lo stato di avanzamento della ricerca
 * @param {string} researchId - ID della ricerca
 * @param {number} groupIndex - Indice del gruppo di task
 */
function pollResearchProgress(researchId, groupIndex) {
    fetch(`/research/${researchId}/check-research-progress/${groupIndex}`)
    .then(response => response.json())
    .then(data => {
        if (data.completed) {
            // La ricerca è completata, ricarichiamo la pagina
            location.reload();
        } else if (data.in_progress) {
            // Aggiorniamo lo stato dei task
            updateTasksStatus(groupIndex, data);
            
            // Controlliamo nuovamente lo stato tra 2 secondi
            setTimeout(() => pollResearchProgress(researchId, groupIndex), 2000);
        } else {
            // La ricerca è stata interrotta per qualche motivo
            const button = document.querySelector(`#task-group-${groupIndex} .research-btn`);
            button.disabled = false;
            button.textContent = "Avvia Ricerca";
        }
    })
    .catch(error => {
        console.error("Errore nel controllo dello stato:", error);
        // Riproviamo dopo un po'
        setTimeout(() => pollResearchProgress(researchId, groupIndex), 5000);
    });
}

/**
 * Aggiorna lo stato dei task in base ai dati ricevuti
 * @param {number} groupIndex - Indice del gruppo di task
 * @param {Object} data - Dati sullo stato dei task
 */
function updateTasksStatus(groupIndex, data) {
    // Prima rimuoviamo la classe 'in-progress' da tutti i task
    const allTasks = document.querySelectorAll(`#task-group-${groupIndex} .task-item`);
    allTasks.forEach(task => {
        task.classList.remove('in-progress');
    });
    
    // Aggiorniamo i task completati
    data.completed_tasks.forEach(taskIndex => {
        const taskElement = document.querySelector(`#task-${groupIndex}-${taskIndex}`);
        if (taskElement) {
            taskElement.classList.add('completed');
            taskElement.classList.remove('in-progress');
            const iconElement = taskElement.querySelector('.completion-icon');
            if (iconElement) {
                iconElement.innerHTML = '✅';
            }
        }
    });
    
    // Evidenziamo il task in corso
    if (data.current_task_index !== null) {
        const currentTaskElement = document.querySelector(`#task-${groupIndex}-${data.current_task_index}`);
        if (currentTaskElement) {
            currentTaskElement.classList.add('in-progress');
            currentTaskElement.classList.remove('completed');
            const iconElement = currentTaskElement.querySelector('.completion-icon');
            if (iconElement && !data.completed_tasks.includes(data.current_task_index)) {
                iconElement.innerHTML = '🔄';
            }
        }
    }
}

/**
 * Inizializza il polling per le ricerche in corso al caricamento della pagina
 */
document.addEventListener('DOMContentLoaded', function() {
    const researchId = document.body.dataset.researchId || '';
    const taskGroups = document.querySelectorAll('.task-group');
    
    taskGroups.forEach((group, index) => {
        const groupIndex = group.id.replace('task-group-', '');
        
        // Verifica se c'è una ricerca in corso
        if (group.querySelector('.research-btn.disabled')) {
            // Se c'è un pulsante di ricerca disabilitato, significa che la ricerca è in corso
            pollResearchProgress(researchId, groupIndex);
        }
    });
});

// Aggiungi qui altre funzioni JavaScript che potrebbero servire in futuro