document.addEventListener('DOMContentLoaded', function() {
    // Автофокус на поле ввода в формах
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        const input = form.querySelector('input[type="text"], input[type="password"]');
        if (input) {
            input.focus();
        }
    });

    // Подтверждение опасных действий
    const dangerousLinks = document.querySelectorAll('a[href*="delete"], a.btn-danger');
    dangerousLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (!confirm('Вы уверены, что хотите выполнить это действие?')) {
                e.preventDefault();
            }
        });
    });

    // Обработка отправки форм с валидацией
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let valid = true;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    valid = false;
                    field.style.borderColor = '#e74c3c';
                } else {
                    field.style.borderColor = '';
                }
            });

            if (!valid) {
                e.preventDefault();
                alert('Пожалуйста, заполните все обязательные поля');
            }
        });
    });
});

// Функции для работы с чатом
function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}