// route.js
document.addEventListener('DOMContentLoaded', function () {
    const pointsContainer = document.getElementById('points-container');
    const addPointBtn = document.getElementById('add-point');
    let pointCount = pointsContainer.querySelectorAll('.point-block').length;

    // Инициализация Sortable для drag-and-drop
    Sortable.create(pointsContainer, {
        animation: 150,
        handle: '.point-block',
        onEnd: function () {
            updatePointOrder();
        }
    });

    // Переключение между destination и custom_name
    function initializePointTypeSelect(block) {
        const select = block.querySelector('.point-type-select');
        const destinationField = block.querySelector('.destination-field');
        const customNameField = block.querySelector('.custom-name-field');
        const destinationInput = block.querySelector('select[name$="-destination"]');
        const customNameInput = block.querySelector('input[name$="-custom_name"]');

        select.addEventListener('change', function () {
            if (select.value === 'destination') {
                destinationField.style.display = 'block';
                customNameField.style.display = 'none';
                customNameInput.value = '';
                destinationInput.value = '';
                $(destinationInput).selectpicker('val', '').selectpicker('refresh');
            } else {
                destinationField.style.display = 'none';
                customNameField.style.display = 'block';
                destinationInput.value = '';
                customNameInput.value = '';
                $(destinationInput).selectpicker('val', '').selectpicker('refresh');
            }
        });
    }

    // Инициализация bootstrap-select для всех точек
    function initializeSelectPicker(block) {
        const destinationInput = block.querySelector('select[name$="-destination"]');
        if (destinationInput) {
            $(destinationInput).selectpicker({
                noneSelectedText: 'Выберите место',
                noneResultsText: 'Нет результатов для {0}',
                liveSearchPlaceholder: 'Поиск места...'
            }).val('').selectpicker('refresh');
        }
    }

    // Инициализация существующих точек
    pointsContainer.querySelectorAll('.point-block').forEach(block => {
        initializePointTypeSelect(block);
        initializeSelectPicker(block);
    });

    // Добавление новой точки
    addPointBtn.addEventListener('click', function () {
        const template = pointsContainer.querySelector('.point-block').cloneNode(true);
        pointCount++;
        template.dataset.pointId = pointCount - 1;
        template.querySelector('.point-header span').textContent = `Точка ${pointCount}`;

        // Обновление имен полей для formset
        const inputs = template.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            const name = input.name.replace(/points-(\d+)-/, `points-${pointCount-1}-`);
            input.name = name;
            input.id = input.id.replace(/id_points-(\d+)-/, `id_points-${pointCount-1}-`);
            if (input.tagName === 'INPUT' && input.type === 'checkbox') input.checked = false;
            else if (input.tagName === 'INPUT' && input.type !== 'file') input.value = '';
            else if (input.tagName === 'TEXTAREA') input.value = '';
            else if (input.tagName === 'SELECT' && input.name.includes('destination')) {
                input.selectedIndex = 0;
                input.value = '';
            }
        });

        // Сбрасываем переключатель на "destination"
        const select = template.querySelector('.point-type-select');
        select.value = 'destination';
        template.querySelector('.destination-field').style.display = 'block';
        template.querySelector('.custom-name-field').style.display = 'none';

        pointsContainer.appendChild(template);
        initializePointTypeSelect(template);
        initializeSelectPicker(template);
        updatePointOrder();
    });

    // Удаление точки
    pointsContainer.addEventListener('click', function (e) {
        if (e.target.classList.contains('remove-point')) {
            e.target.closest('.point-block').remove();
            pointCount--;
            updatePointOrder();
        }
    });

    // Обновление порядка и номеров точек
    function updatePointOrder() {
        const blocks = pointsContainer.querySelectorAll('.point-block');
        blocks.forEach((block, index) => {
            block.querySelector('.point-header span').textContent = `Точка ${index + 1}`;
            const inputs = block.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.name = input.name.replace(/points-\d+-/, `points-${index}-`);
                input.id = input.id.replace(/id_points-\d+-/, `id_points-${index}-`);
            });
        });
        document.querySelector('#id_points-TOTAL_FORMS').value = blocks.length;
    }
});
