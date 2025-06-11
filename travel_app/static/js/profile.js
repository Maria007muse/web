document.addEventListener('DOMContentLoaded', function () {
    const postModal = document.getElementById('postModal');
    postModal.addEventListener('show.bs.modal', function (event) {
        const postCard = event.relatedTarget;
        const postId = postCard.getAttribute('data-post-id');
        const postImage = postCard.getAttribute('data-post-image');
        const postTitle = postCard.getAttribute('data-post-title');
        const postDescription = postCard.getAttribute('data-post-description');
        const postAuthor = postCard.getAttribute('data-post-author');
        const postDate = postCard.getAttribute('data-post-date');
        const postLikes = postCard.getAttribute('data-post-likes');

        const modalTitle = postModal.querySelector('.modal-title');
        const modalImage = postModal.querySelector('#postModalImage');
        const modalDescription = postModal.querySelector('#postModalDescription');
        const modalAuthor = postModal.querySelector('#postModalAuthor');
        const modalDate = postModal.querySelector('#postModalDate');
        const modalLikes = postModal.querySelector('#postModalLikes');

        modalTitle.textContent = postTitle;
        modalImage.src = postImage;
        modalDescription.textContent = postDescription;
        modalAuthor.textContent = `Автор: ${postAuthor}`;
        modalDate.textContent = `Дата: ${postDate}`;
        modalLikes.textContent = `Лайков: ${postLikes}`;
    });
});
