(function () {
    const heightInput = document.getElementById('height_cm');
    const weightInput = document.getElementById('weight_kg');
    const bmiInput = document.getElementById('bmi');
    const genderSelect = document.getElementById('gender');
    const pregnanciesGroup = document.getElementById('pregnanciesGroup');

    function calcBmi() {
        const h = parseFloat(heightInput?.value);
        const w = parseFloat(weightInput?.value);
        if (h > 0 && w > 0 && bmiInput) {
            bmiInput.value = (w / ((h / 100) ** 2)).toFixed(1);
        }
    }

    function togglePregnancies() {
        if (!pregnanciesGroup || !genderSelect) return;
        const isMale = genderSelect.value === 'male';
        pregnanciesGroup.hidden = isMale;
        if (isMale) {
            const pregInput = document.getElementById('pregnancies');
            if (pregInput) pregInput.value = '0';
        }
    }

    heightInput?.addEventListener('input', calcBmi);
    weightInput?.addEventListener('input', calcBmi);
    genderSelect?.addEventListener('change', togglePregnancies);

    document.querySelectorAll('.guide-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = 'guide-' + btn.dataset.guide;
            const panel = document.getElementById(id);
            if (panel) {
                const open = panel.hidden;
                document.querySelectorAll('.guide-panel').forEach(p => p.hidden = true);
                panel.hidden = !open;
            }
        });
    });

    calcBmi();
    togglePregnancies();
})();
