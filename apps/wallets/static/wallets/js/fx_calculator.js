document.addEventListener('DOMContentLoaded', () => {
    const currencySymbols = {
        'GBP': '£',
        'USD': '$',
        'EUR': '€'
    };

    const fxForm = document.getElementById('fx-form');
    if (!fxForm) {
        return;
    }


    const fxRates = JSON.parse(fxForm.dataset.fxRates);

    const fromSymbolSpans = document.getElementsByClassName('fx-from-symbol');
    const fxRateSpan = document.getElementById('fx-rate');


    function updateExchangeRateDisplay() {
        const fromCurrency = document.getElementById('id_from_wallet_currency').value;
        const fromSymbol = currencySymbols[fromCurrency] || fromCurrency;

        Array.from(fromSymbolSpans).forEach(span => {
            span.textContent = fromSymbol;
        });

        const exchangeRate = parseFloat(fxRates[fromCurrency]);
        fxRateSpan.textContent = (Math.round(exchangeRate * 100) / 100).toFixed(4);

    }

    

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
            convertedAmountSpan.textContent = '0.00';
            return;
        }

        const exchangeRate = parseFloat(fxRates[fromCurrency]);

        if (isNaN(exchangeRate)) {
            convertedAmountSpan.textContent = 'Error: FX rate not available.';
            return;
        }

        const fromAmount = toAmount * exchangeRate;

        convertedAmountSpan.textContent = `${formatNumberWithCommas(fromAmount)}`;
    }

    toAmountInput.addEventListener('keyup', updateConvertedAmount);
    fromWalletSelect.addEventListener('change', updateConvertedAmount);
    fromWalletSelect.addEventListener('change', updateExchangeRateDisplay);

    // Initial calculation on page load if there's a value
    updateConvertedAmount();
    updateExchangeRateDisplay();
});
