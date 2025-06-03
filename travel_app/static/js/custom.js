$(document).ready(function() {
    console.log("custom.js loaded and jQuery is ready");
    // Для search.html
    setDefaultValues();

    // Для profile.html
    $('.nav-tabs a').click(function (e) {
        e.preventDefault();
        $(this).tab('show');
    });

    // Для review.html
    var selectedStarValue = 0;

    function hoverStars(value) {
        if (selectedStarValue === 0) {
            $('.star').removeClass('selected');
            $('.star[data-value="' + value + '"]').prevAll('.star').addBack().addClass('selected');
        }
    }

    $('.star').hover(function() {
        var value = $(this).data('value');
        hoverStars(value);
    }, function() {
        if (selectedStarValue === 0) {
            $('.star').removeClass('selected');
        }
    });

    $('.star').on('click', function() {
        var value = $(this).data('value');
        console.log('Star clicked, value:', value);
        $('.star').removeClass('selected');
        $(this).prevAll('.star').addBack().addClass('selected');
        selectedStarValue = value;
        $('#rating-input').val(value);
        console.log('Rating input value:', $('#rating-input').val());
    });

    var initialRating = $('#rating-input').val();
    if (initialRating > 0) {
        $('.star[data-value="' + initialRating + '"]').prevAll('.star').addBack().addClass('selected');
        selectedStarValue = initialRating;
    }

    var commentBox = $('#comment-box');
    var charCount = $('#char-count');
    commentBox.on('input', function() {
        var textLength = commentBox.val().length;
        charCount.text(textLength + '/50 символов');
    });
    charCount.text(commentBox.val().length + '/50 символов');

    // Добавляем проверку перед отправкой формы
    $('form').on('submit', function(e) {
        var rating = $('#rating-input').val();
        if (rating == 0) {
            e.preventDefault();
            alert('Пожалуйста, выберите рейтинг от 1 до 5.');
        }
    });
});

// Для search.html

