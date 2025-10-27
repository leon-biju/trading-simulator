const walletCards = document.querySelectorAll('.wallet-card');

walletCards.forEach(card => {
    card.addEventListener('click', () => {
        const currency = card.id;
        window.location.href = `/wallets/${currency}/`;
    });
});