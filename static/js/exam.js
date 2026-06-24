/* Exam-taking interface logic */
(function () {
    const cfg = window.EXAM_CONFIG;
    let currentSectionId = cfg.sections.length ? cfg.sections[0].id : null;
    let currentQuestionId = cfg.sections.length ? cfg.sections[0].questions[0].id : null;
    let currentChoiceId = null;
    let timeLeft = cfg.timeLeftSeconds;

    // ---------------- Timer ----------------
    function formatTime(sec) {
        const h = Math.floor(sec / 3600);
        const m = Math.floor((sec % 3600) / 60);
        const s = sec % 60;
        return [h, m, s].map(v => String(v).padStart(2, '0')).join(':');
    }

    function tickTimer() {
        if (timeLeft <= 0) {
            document.getElementById('timer').textContent = '00:00:00';
            autoSubmit();
            return;
        }
        timeLeft -= 1;
        document.getElementById('timer').textContent = formatTime(timeLeft);
    }
    document.getElementById('timer').textContent = formatTime(timeLeft);
    setInterval(tickTimer, 1000);

    function autoSubmit() {
        fetch(cfg.urls.autoSubmit, {
            headers: { 'X-CSRFToken': cfg.csrfToken }
        }).then(() => { window.location.href = cfg.urls.result; });
    }

    // ---------------- Section tabs ----------------
    document.querySelectorAll('.section-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.section-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentSectionId = parseInt(tab.dataset.sectionId, 10);
            const section = cfg.sections.find(s => s.id === currentSectionId);
            document.getElementById('palette-subject-title').textContent = section.subject;
            loadQuestion(section.questions[0].id);
            renderPalette();
        });
    });

    // ---------------- Load a question ----------------
    function loadQuestion(questionId) {
        currentQuestionId = questionId;
        const url = cfg.urls.getQuestion.replace('__QID__', questionId);
        fetch(url)
            .then(r => r.json())
            .then(data => {
                document.getElementById('question-number').textContent = data.order;
                document.getElementById('question-text').textContent = data.text;
                currentChoiceId = data.selected_choice_id;

                const list = document.getElementById('choices-list');
                list.innerHTML = '';
                data.choices.forEach((choice, idx) => {
                    const id = 'choice-' + choice.id;
                    const row = document.createElement('label');
                    row.className = 'choice-row';
                    row.innerHTML = `
                        <input type="radio" name="choice" value="${choice.id}" id="${id}"
                               ${data.selected_choice_id === choice.id ? 'checked' : ''}>
                        <span>${choice.text}</span>
                    `;
                    row.querySelector('input').addEventListener('change', () => {
                        currentChoiceId = choice.id;
                    });
                    list.appendChild(row);
                });

                renderPalette();

                if (window.MathJax) {
                    MathJax.typesetPromise([document.getElementById('question-text'), list]);
                }
            });
    }

    // ---------------- Save / Clear / Mark actions ----------------
    function postAnswer(action, thenAdvance) {
        fetch(cfg.urls.saveAnswer, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': cfg.csrfToken
            },
            body: JSON.stringify({
                question_id: currentQuestionId,
                choice_id: currentChoiceId,
                action: action
            })
        }).then(r => r.json()).then(() => {
            renderPalette();
            if (thenAdvance) goToNextQuestion();
        });
    }

    function goToNextQuestion() {
        const section = cfg.sections.find(s => s.id === currentSectionId);
        const idx = section.questions.findIndex(q => q.id === currentQuestionId);
        if (idx >= 0 && idx < section.questions.length - 1) {
            loadQuestion(section.questions[idx + 1].id);
        }
    }

    document.getElementById('btn-save-next').addEventListener('click', () => postAnswer('save', true));
    document.getElementById('btn-clear').addEventListener('click', () => {
        currentChoiceId = null;
        document.querySelectorAll('#choices-list input[type=radio]').forEach(r => r.checked = false);
        postAnswer('clear', false);
    });
    document.getElementById('btn-mark-review').addEventListener('click', () => postAnswer('mark_review', true));

    // ---------------- Palette ----------------
    function statusClass(status) {
        return {
            'NOT_VISITED': 'pal-notvisited',
            'NOT_ANSWERED': 'pal-notanswered',
            'ANSWERED': 'pal-answered',
            'MARKED_FOR_REVIEW': 'pal-marked',
            'ANSWERED_MARKED': 'pal-answered-marked'
        }[status] || 'pal-notvisited';
    }

    function renderPalette() {
        fetch(cfg.urls.palette)
            .then(r => r.json())
            .then(data => {
                const counts = { NOT_VISITED: 0, NOT_ANSWERED: 0, ANSWERED: 0, MARKED_FOR_REVIEW: 0, ANSWERED_MARKED: 0 };
                const sectionQuestions = data.sections[currentSectionId] || [];

                // counts across ALL sections (matches typical EAPCET-style global counters)
                Object.values(data.sections).forEach(qs => {
                    qs.forEach(q => { counts[q.status] = (counts[q.status] || 0) + 1; });
                });

                document.getElementById('count-not-visited').textContent = counts.NOT_VISITED;
                document.getElementById('count-not-answered').textContent = counts.NOT_ANSWERED;
                document.getElementById('count-answered').textContent = counts.ANSWERED;
                document.getElementById('count-marked').textContent = counts.MARKED_FOR_REVIEW;
                document.getElementById('count-answered-marked').textContent = counts.ANSWERED_MARKED;

                const grid = document.getElementById('palette-grid');
                grid.innerHTML = '';
                sectionQuestions.forEach(q => {
                    const btn = document.createElement('button');
                    btn.className = 'palette-cell ' + statusClass(q.status);
                    if (q.question_id === currentQuestionId) btn.classList.add('current');
                    btn.textContent = q.order;
                    btn.addEventListener('click', () => loadQuestion(q.question_id));
                    grid.appendChild(btn);
                });
            });
    }

    // ---------------- Submit ----------------
    const modal = document.getElementById('submit-modal');
    document.getElementById('btn-submit').addEventListener('click', () => {
        modal.classList.add('open');
    });
    document.getElementById('modal-cancel').addEventListener('click', () => {
        modal.classList.remove('open');
    });
    document.getElementById('modal-confirm').addEventListener('click', () => {
        fetch(cfg.urls.submit, {
            method: 'POST',
            headers: { 'X-CSRFToken': cfg.csrfToken }
        }).then(() => { window.location.href = cfg.urls.result; });
    });

    // ---------------- Init ----------------
    loadQuestion(currentQuestionId);
})();
