document.addEventListener('DOMContentLoaded', () => {
    $('.selectpicker').selectpicker();

    // Объект для хранения состояния фильтров
    let filtersState = {
        tags: [], // массив выбранных тегов
    };

    // Функция для обновления количества выбранных опций в selectpicker
    function updateSelectedCount(selectElement) {
        const wrapper = selectElement.closest('.selectpicker-wrapper');
        if (!wrapper) return;
        const countSpan = wrapper.querySelector('.selected-count');
        if (!countSpan) return;
        const selectedCount = selectElement.selectedOptions.length;
        countSpan.textContent = selectedCount > 0 ? selectedCount : '';
    }

    // Функция для обновления общего количества выбранных фильтров
    function updateTotalSelectedCount() {
        const form = document.getElementById('quickSearchForm');
        const inputs = form.querySelectorAll('input, select, textarea');

        let totalCount = 0;

        inputs.forEach(input => {
            if (input.type === 'checkbox') {
                if (input.checked) totalCount++;
            } else if (input.tagName === 'SELECT' && input.multiple) {
                const selected = Array.from(input.selectedOptions).filter(opt => opt.value);
                if (selected.length > 0) totalCount++;
            } else {
                if (input.value && input.value.trim() !== '') totalCount++;
            }
        });

        const totalSelectedCountElement = document.getElementById('totalSelectedCount');
        if (totalSelectedCountElement) {
            if (totalCount > 0) {
                totalSelectedCountElement.textContent = totalCount;
                totalSelectedCountElement.style.display = 'inline-block';
            } else {
                totalSelectedCountElement.style.display = 'none';
            }
        }
    }

    // Инициализация и обновление состояния тегов
    function syncTagCheckboxes(formId, tagValue, isChecked) {
        const checkbox = document.querySelector(`#${formId} input[name="tags"][value="${tagValue}"]`);
        if (checkbox) {
            checkbox.checked = isChecked;
            const tagCheckbox = checkbox.parentElement;
            if (isChecked) {
                tagCheckbox.classList.add('selected');
                if (!filtersState.tags.includes(tagValue)) {
                    filtersState.tags.push(tagValue);
                }
            } else {
                tagCheckbox.classList.remove('selected');
                filtersState.tags = filtersState.tags.filter(tag => tag !== tagValue);
            }
        }
    }

    // Обработчики для selectpicker
    document.querySelectorAll('.selectpicker').forEach(select => {
        updateSelectedCount(select);
        select.addEventListener('change', () => {
            updateSelectedCount(select);
            updateTotalSelectedCount();
        });
    });

    // Обработчики для остальных элементов малого окна
    document.querySelectorAll('#quickSearchForm input, #quickSearchForm select').forEach(el => {
        el.addEventListener('change', updateTotalSelectedCount);
    });

    updateTotalSelectedCount();

    // Переключение вида (сетка/список)
    const resultsGrid = document.getElementById('resultsGrid');
    const viewButtons = document.querySelectorAll('.view-btn');

    viewButtons.forEach(button => {
        button.addEventListener('click', () => {
            viewButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            resultsGrid.dataset.view = button.dataset.view;
        });
    });

    // Инициализация тегов в малом окне
    document.querySelectorAll('#quickSearchForm .tag-checkbox input[type="checkbox"]').forEach(checkbox => {
        const tagValue = checkbox.value;
        if (checkbox.checked) {
            if (!filtersState.tags.includes(tagValue)) {
                filtersState.tags.push(tagValue);
                checkbox.parentElement.classList.add('selected');
            }
        }
        checkbox.addEventListener('change', function() {
            const isChecked = this.checked;
            const tagValue = this.value;
            syncTagCheckboxes('quickSearchForm', tagValue, isChecked);
            syncTagCheckboxes('fullSearchForm', tagValue, isChecked);
            console.log('Текущее состояние тегов (малое окно):', filtersState.tags);
            updateTotalSelectedCount();
        });
    });

    // Синхронизация при открытии полного окна
    document.querySelector('[data-target="#allFiltersModal"]').addEventListener('click', function() {
        const quickInputs = document.querySelectorAll('#quickSearchForm input, #quickSearchForm select');
        const fullForm = document.getElementById('fullSearchForm');

        quickInputs.forEach(input => {
            const fullInput = fullForm.querySelector(`[name="${input.name}"]`);
            if (!fullInput) return;

            if (input.type === 'checkbox') {
                fullInput.checked = input.checked;
            } else if (input.multiple) {
                Array.from(fullInput.options).forEach(option => {
                    option.selected = Array.from(input.selectedOptions).some(selected => selected.value === option.value);
                });
            } else {
                fullInput.value = input.value;
            }
        });

        // Синхронизация тегов в полном окне
        document.querySelectorAll('#fullSearchForm .tag-checkbox input[type="checkbox"]').forEach(checkbox => {
            const tagValue = checkbox.value;
            const isChecked = filtersState.tags.includes(tagValue);
            syncTagCheckboxes('fullSearchForm', tagValue, isChecked);
        });

        $(fullForm).find('.selectpicker').selectpicker('refresh');
        fullForm.querySelectorAll('.selectpicker').forEach(select => updateSelectedCount(select));
    });

    // Обработчики для тегов в полном окне
    document.querySelectorAll('#fullSearchForm .tag-checkbox input[type="checkbox"]').forEach(checkbox => {
        const tagValue = checkbox.value;
        if (checkbox.checked) {
            if (!filtersState.tags.includes(tagValue)) {
                filtersState.tags.push(tagValue);
                checkbox.parentElement.classList.add('selected');
            }
        }
        checkbox.addEventListener('change', function() {
            const isChecked = this.checked;
            const tagValue = this.value;
            syncTagCheckboxes('fullSearchForm', tagValue, isChecked);
            syncTagCheckboxes('quickSearchForm', tagValue, isChecked);
            console.log('Текущее состояние тегов (полное окно):', filtersState.tags);
            updateTotalSelectedCount();
        });
    });

    // Обратная синхронизация при отправке полной формы
    const quickForm = document.getElementById('quickSearchForm');
    const fullForm = document.getElementById('fullSearchForm');

    fullForm.addEventListener('submit', () => {
        const fullInputs = fullForm.querySelectorAll('input, select');

        fullInputs.forEach(input => {
            const quickInput = quickForm.querySelector(`[name="${input.name}"]`);
            if (!quickInput) return;

            if (input.type === 'checkbox') {
                syncTagCheckboxes('quickSearchForm', input.value, input.checked);
            } else if (input.multiple) {
                Array.from(quickInput.options).forEach(option => {
                    option.selected = Array.from(input.selectedOptions).some(selected => selected.value === option.value);
                });
            } else {
                quickInput.value = input.value;
            }
        });

        $(quickForm).find('.selectpicker').selectpicker('refresh');
    });

    // Прокрутка к результатам при отправке формы
    [quickForm, fullForm].forEach(form => {
        form.addEventListener('submit', () => {
            setTimeout(() => {
                const grid = document.querySelector('.results-grid');
                if (grid) {
                    window.scrollTo({
                        top: grid.offsetTop,
                        behavior: 'smooth'
                    });
                }
            }, 100);
        });
    });

    // Добавление в избранное
    document.querySelectorAll('.btn-favorite').forEach(button => {
        button.addEventListener('click', async () => {
            const pk = button.dataset.pk;
            try {
                const response = await fetch(`/toggle_favorite/${pk}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                    },
                });
                if (response.ok) {
                    button.classList.toggle('active');
                }
            } catch (error) {
                console.error('Ошибка при добавлении в избранное:', error);
            }
        });
    });

    // Горизонтальный скролл рекомендованных
    const slider = document.querySelector('.recommended-slider');
    if (slider) {
        let isDown = false;
        let startX;
        let scrollLeft;

        slider.addEventListener('mousedown', (e) => {
            isDown = true;
            startX = e.pageX - slider.offsetLeft;
            scrollLeft = slider.scrollLeft;
        });

        slider.addEventListener('mouseleave', () => isDown = false);
        slider.addEventListener('mouseup', () => isDown = false);

        slider.addEventListener('mousemove', (e) => {
            if (!isDown) return;
            e.preventDefault();
            const x = e.pageX - slider.offsetLeft;
            const walk = (x - startX) * 2;
            slider.scrollLeft = scrollLeft - walk;
        });
    }
});
