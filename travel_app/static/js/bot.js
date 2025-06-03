document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.querySelector('#chat-form');
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const input = chatForm.querySelector('input[name="message"]');
        const message = input.value;
        const chatOutput = document.querySelector('#chat-output');
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        console.log("Отправляемый текст:", message);

        // Показ запроса пользователя
        chatOutput.innerHTML += `<p><strong>Вы:</strong> ${message}</p>`;

        // Формирование тела запроса корректно!
        const formData = new URLSearchParams();
        formData.append('message', message);
        formData.append('csrfmiddlewaretoken', csrfToken);

        const response = await fetch('/chatbot/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        });

        const data = await response.json();
        chatOutput.innerHTML += `<p><strong>Бот:</strong> ${data.reply}</p>`;
        chatOutput.scrollTop = chatOutput.scrollHeight;
        input.value = '';
    });
});
