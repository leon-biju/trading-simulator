document.addEventListener('DOMContentLoaded', function() {
    const amountInput = document.getElementById('id_to_amount');
    
    if (amountInput) {
        amountInput.addEventListener('blur', function(e) {
            const value = parseFloat(e.target.value);
            
            if (isNaN(value) || value <= 0) {
                e.target.setCustomValidity('Please enter a valid amount greater than 0');
                e.target.reportValidity();
            } else {
                e.target.setCustomValidity('');
                e.target.value = value.toFixed(2);
            }
        });
    }
});