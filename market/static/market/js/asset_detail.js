document.addEventListener('DOMContentLoaded', function() {
    const orderTypeSelect = document.getElementById('order_type');
    const limitPriceGroup = document.getElementById('limitPriceGroup');
    const limitPriceInput = document.getElementById('limit_price');
    const orderTypeHelp = document.getElementById('orderTypeHelp');
    const quantityInput = document.getElementById('quantity');
    const sideBuy = document.getElementById('sideBuy');
    const sideSell = document.getElementById('sideSell');
    const submitBtn = document.getElementById('submitBtn');
    const submitBtnText = document.getElementById('submitBtnText');
    const estimatedAmount = document.getElementById('estimatedAmount');
    const amountLabel = document.getElementById('amountLabel');
    
    
    const currentPrice = JSON.parse(document.getElementById('current_price').textContent);
    const currencyCode = JSON.parse(document.getElementById('currency_code').textContent);
    const availableBalance = JSON.parse(document.getElementById('available_balance').textContent);
    const availableQuantity = JSON.parse(document.getElementById('available_quantity').textContent);
    
    function updateOrderTypeUI() {
        if (orderTypeSelect.value === 'LIMIT') {
            limitPriceGroup.style.display = 'block';
            limitPriceInput.required = true;
            orderTypeHelp.textContent = 'Execute when price reaches your limit.';
        } else {
            limitPriceGroup.style.display = 'none';
            limitPriceInput.required = false;
            orderTypeHelp.textContent = 'Execute immediately at current market price.';
        }
        updateEstimate();
    }
    
    function updateSideUI() {
        const isBuy = sideBuy.checked;
        submitBtn.classList.remove('btn-success', 'btn-danger', 'btn-primary');
        
        if (isBuy) {
            submitBtn.classList.add('btn-success');
            submitBtnText.textContent = 'Place Buy Order';
            amountLabel.textContent = 'Cost';

        } else {
            submitBtn.classList.add('btn-danger');
            submitBtnText.textContent = 'Place Sell Order';
            amountLabel.textContent = 'Proceeds';
        }
        updateEstimate();
    }
    
    function updateEstimate() {
        const quantity = parseFloat(quantityInput.value) || 0;
        const isBuy = sideBuy.checked;
        let price = currentPrice;
        
        if (orderTypeSelect.value === 'LIMIT') {
            price = parseFloat(limitPriceInput.value) || currentPrice;
        }
        
        if (quantity > 0 && price) {
            const total = (quantity * price).toFixed(2);
            const fee = (quantity * price * 0.001).toFixed(2);
            
            if (isBuy) {
                const totalWithFee = (parseFloat(total) + parseFloat(fee)).toFixed(2);
                estimatedAmount.innerHTML = `${currencyCode} ${total} + ${currencyCode} ${fee} fee = <strong>${currencyCode} ${totalWithFee}</strong>`;
                
                if (parseFloat(totalWithFee) > availableBalance) {
                    estimatedAmount.innerHTML += ' <span class="text-danger">(Insufficient funds)</span>';
                }
            } else {
                const netProceeds = (parseFloat(total) - parseFloat(fee)).toFixed(2);
                estimatedAmount.innerHTML = `${currencyCode} ${total} - ${currencyCode} ${fee} fee = <strong>${currencyCode} ${netProceeds}</strong>`;
                if (quantity > availableQuantity) {
                    estimatedAmount.innerHTML += ' <span class="text-danger">(Insufficient holdings)</span>';
                }
            }
        } else {
            estimatedAmount.textContent = '—';
        }
    }
    
    // Event listeners
    if (orderTypeSelect) {
        orderTypeSelect.addEventListener('change', updateOrderTypeUI);
    }
    if (sideBuy) {
        sideBuy.addEventListener('change', updateSideUI);
    }
    if (sideSell) {
        sideSell.addEventListener('change', updateSideUI);
    }
    if (quantityInput) {
        quantityInput.addEventListener('input', updateEstimate);
    }
    if (limitPriceInput) {
        limitPriceInput.addEventListener('input', updateEstimate);
    }
    
    // Initialize
    updateOrderTypeUI();
    updateSideUI();
});
