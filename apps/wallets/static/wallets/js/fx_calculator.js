document.addEventListener('DOMContentLoaded', () => {
    const fxForm = document.getElementById('fx-form');
    if (!fxForm) {
        return;
    }
    console.log(fxForm.dataset);
    const fxRates = JSON.parse(fxForm.dataset.fxRates);
    console.log('FX Rates:', fxRates);
    const toCurrency = fxForm.dataset.toCurrency;

    const currencySymbols = {
        'GBP': '£',
        'USD': '$',
        'EUR': '€'
    };

    const toAmountInput = document.getElementById('id_to_amount');
    const fromWalletSelect = document.getElementById('id_from_wallet_currency');
    const convertedAmountSpan = document.getElementById('converted-amount');

    function formatNumberWithCommas(number) {
        return number.toLocaleString('en-GB', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    function updateConvertedAmount() {
        const toAmount = parseFloat(toAmountInput.value);
        const fromCurrency = fromWalletSelect.value;

        if (isNaN(toAmount) || toAmount <= 0 || !fromCurrency) {
            convertedAmountSpan.textContent = '';
            return;
        }

        const fromRate = parseFloat(fxRates[fromCurrency]);
        const toRate = parseFloat(fxRates[toCurrency]);

        if (isNaN(fromRate) || isNaN(toRate)) {
            convertedAmountSpan.textContent = 'Error: FX rate not available.';
            return;
        }

        const fromAmount = (toAmount / toRate) * fromRate;
        const fromSymbol = currencySymbols[fromCurrency] || fromCurrency;

        convertedAmountSpan.textContent = `${fromSymbol}${formatNumberWithCommas(fromAmount)}`;
    }

    toAmountInput.addEventListener('keyup', updateConvertedAmount);
    fromWalletSelect.addEventListener('change', updateConvertedAmount);

    // Initial calculation on page load if there's a value
    updateConvertedAmount();
});
