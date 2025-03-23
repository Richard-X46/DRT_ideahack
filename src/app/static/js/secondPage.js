document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const sourceInput = document.getElementById('source');
    const destInput = document.getElementById('destination');
    const lookupSourceBtn = document.getElementById('lookupSourceBtn');
    const lookupDestBtn = document.getElementById('lookupDestBtn');
    const sourceAddressList = document.getElementById('sourceAddressList');
    const destAddressList = document.getElementById('destAddressList');
    const getMapBtn = document.getElementById('getMapBtn');
    const mapContainer = document.getElementById('map-container');

    // Track selected addresses
    let selectedSource = '';
    let selectedDest = '';

    // Add loading indicator
    function setLoading(button, isLoading) {
        button.disabled = isLoading;
        button.textContent = isLoading ? 'Loading...' : button.dataset.originalText || button.textContent;
    }

    // Save original button text
    [lookupSourceBtn, lookupDestBtn, getMapBtn].forEach(btn => {
        btn.dataset.originalText = btn.textContent;
    });

    async function lookupAddress(query, listElement, inputElement) {
        if (!query || query.length < 3) {
            alert('Please enter at least 3 characters');
            return;
        }

        try {
            setLoading(inputElement === sourceInput ? lookupSourceBtn : lookupDestBtn, true);
            
            const response = await fetch(`/address-suggestions?query=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Clear and hide previous suggestions
            listElement.innerHTML = '';
            
            if (!data.suggestions || data.suggestions.length === 0) {
                listElement.innerHTML = '<li class="no-results">No addresses found</li>';
                listElement.style.display = 'block';
                return;
            }
            
            // Add new suggestions
            data.suggestions.forEach(address => {
                const li = document.createElement('li');
                li.textContent = address;
                li.addEventListener('click', () => {
                    inputElement.value = address;
                    listElement.style.display = 'none';
                    
                    // Update selected addresses
                    if (listElement === sourceAddressList) {
                        selectedSource = address;
                    } else {
                        selectedDest = address;
                    }
                    
                    // Enable get map button if both addresses are selected
                    getMapBtn.disabled = !(selectedSource && selectedDest);
                });
                listElement.appendChild(li);
            });
            
            // Show the suggestions list
            listElement.style.display = 'block';
            
        } catch (error) {
            console.error('Error:', error);
            alert('Error looking up address: ' + error.message);
        } finally {
            setLoading(inputElement === sourceInput ? lookupSourceBtn : lookupDestBtn, false);
        }
    }

    // Event listeners for lookup buttons
    lookupSourceBtn.addEventListener('click', () => {
        lookupAddress(sourceInput.value.trim(), sourceAddressList, sourceInput);
    });

    lookupDestBtn.addEventListener('click', () => {
        lookupAddress(destInput.value.trim(), destAddressList, destInput);
    });

    // Event listener for map generation
    getMapBtn.addEventListener('click', async () => {
        if (!selectedSource || !selectedDest) {
            alert('Please select both source and destination addresses');
            return;
        }

        try {
            setLoading(getMapBtn, true);
            mapContainer.innerHTML = '<div class="loading">Loading map...</div>';
            
            const response = await fetch('/get_map', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    source: selectedSource,
                    destination: selectedDest
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const mapHtml = await response.text();
            mapContainer.innerHTML = mapHtml;
            
        } catch (error) {
            console.error('Error:', error);
            mapContainer.innerHTML = `<div class="error">Error generating map: ${error.message}</div>`;
            alert('Error generating map: ' + error.message);
        } finally {
            setLoading(getMapBtn, false);
        }
    });

    // Close suggestion lists when clicking outside
    document.addEventListener('click', (event) => {
        if (!event.target.closest('.address-container')) {
            sourceAddressList.style.display = 'none';
            destAddressList.style.display = 'none';
        }
    });

    // Add input event listeners for real-time validation
    [sourceInput, destInput].forEach(input => {
        input.addEventListener('input', () => {
            input.classList.toggle('invalid', input.value.length > 0 && input.value.length < 3);
        });
    });
});