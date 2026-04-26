/**
 * SaaS Dashboard Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    const productsContainer = document.getElementById('products-list');
    const addProductBtn = document.getElementById('add-product-btn');
    const configForm = document.getElementById('config-form');
    const embedCodeEl = document.getElementById('embed-code');
    const statusBadge = document.getElementById('status-badge');
    const copyBtn = document.getElementById('copy-btn');

    // --- Helper: Add Product Row ---
    function addProductRow(name = '', price = '') {
        const div = document.createElement('div');
        div.className = 'product-item';
        div.innerHTML = `
            <input type="text" placeholder="Product Name" value="${name}" class="p-name">
            <input type="text" placeholder="Price" value="${price}" class="p-price">
            <button type="button" class="remove-btn">×</button>
        `;
        div.querySelector('.remove-btn').onclick = () => div.remove();
        productsContainer.appendChild(div);
    }

    addProductBtn.onclick = () => addProductRow();

    // Default products for the demo
    addProductRow('Apex 75% Mechanical', '149.99');
    addProductRow('Apex TKL Pro', '199.99');

    // --- Form Submission ---
    configForm.onsubmit = async (e) => {
        e.preventDefault();

        const storeName = document.getElementById('store-name').value;
        const systemPrompt = document.getElementById('system-prompt').value;
        
        // Gather products
        const products = Array.from(document.querySelectorAll('.product-item')).map(item => ({
            name: item.querySelector('.p-name').value,
            price: item.querySelector('.p-price').value
        }));

        // Generate a simple API key based on store name (for demo)
        const apiKey = 'key_' + storeName.toLowerCase().replace(/\s+/g, '_') + '_' + Math.floor(Math.random() * 1000);

        const config = {
            apiKey: apiKey,
            storeName: storeName,
            system_instruction: `SYSTEM_PROMPT: You are a sales assistant for ${storeName}.
            
            ## About the Store
            ${systemPrompt}
            
            ## Our Products
            ${products.map(p => `- ${p.name} ($${p.price})`).join('\n')}
            
            Speak exclusively in Darija.`,
            tools: [
                {
                    name: "add_to_cart",
                    description: "Add an item to the shopping cart.",
                    parameters: {
                        type: "OBJECT",
                        properties: {
                            product_id: { type: "STRING" }
                        },
                        required: ["product_id"]
                    }
                }
            ]
        };

        try {
            const response = await fetch('/api/save-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            if (response.ok) {
                const result = await response.json();
                updateEmbedCode(result.apiKey);
                showStatus();
            }
        } catch (err) {
            console.error('Save failed:', err);
            alert('Failed to save configuration.');
        }
    };

    // --- Update Embed Code ---
    function updateEmbedCode(apiKey) {
        const baseUrl = window.location.origin;
        const code = `<!-- ApexVoice AI Assistant -->
<script src="${baseUrl}/cdn/apex-voice.js"></script>
<script>
  ApexVoice.init({
    apiKey: "${apiKey}"
  });
</script>`;
        embedCodeEl.textContent = code;
    }

    function showStatus() {
        statusBadge.style.display = 'block';
        setTimeout(() => {
            statusBadge.style.display = 'none';
        }, 3000);
    }

    // --- Copy Button ---
    copyBtn.onclick = () => {
        navigator.clipboard.writeText(embedCodeEl.textContent);
        const oldText = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        setTimeout(() => copyBtn.textContent = oldText, 2000);
    };
});
