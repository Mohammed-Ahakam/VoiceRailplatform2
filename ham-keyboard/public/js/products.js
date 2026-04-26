/* ============================================
   Apex Keyboards — Product Data & Renderer
   ============================================ */

window.PRODUCTS = [
  {
    id: "apex-75",
    name: "Apex 75% Mechanical",
    price: 149.99,
    switches: "Gateron Pro Brown",
    connectivity: "USB-C / Bluetooth 5.0",
    features: ["Hot-swappable switches", "RGB backlight", "PBT keycaps", "Aluminum frame"],
    description: "The perfect balance of size and functionality. Tactile Gateron Browns give satisfying feedback without the click.",
    inStock: true,
    badge: "Best Seller"
  },
  {
    id: "apex-tkl",
    name: "Apex TKL Pro",
    price: 199.99,
    switches: "Cherry MX Red",
    connectivity: "USB-C / Bluetooth 5.0",
    features: ["Gasket mount", "Sound-dampening foam", "OLED display", "PBT keycaps"],
    description: "Our premium tenkeyless with gasket mount for the smoothest typing experience. Built-in OLED shows your stats.",
    inStock: true,
    badge: "Premium"
  },
  {
    id: "apex-full",
    name: "Apex Full-Size",
    price: 129.99,
    switches: "Gateron Yellow",
    connectivity: "USB-C",
    features: ["Full numpad", "RGB backlight", "ABS keycaps", "Steel plate"],
    description: "Everything you need, nothing you don't. Smooth linear switches and a full numpad for number crunchers.",
    inStock: true,
    badge: null
  },
  {
    id: "apex-60",
    name: "Apex 60% Compact",
    price: 109.99,
    switches: "Kailh Box White",
    connectivity: "USB-C / Bluetooth 5.0",
    features: ["Hot-swappable", "Compact layout", "RGB backlight", "Carrying case included"],
    description: "Ultra-portable with satisfying clicky switches. Comes with a premium carrying case for on-the-go typing.",
    inStock: true,
    badge: "Portable"
  }
];

window.SHIPPING_INFO = {
  standard: { price: 0, days: "5-7 business days", label: "Free Standard Shipping" },
  express: { price: 12.99, days: "2-3 business days", label: "Express Shipping" },
  overnight: { price: 24.99, days: "Next business day", label: "Overnight Shipping" },
  returnPolicy: "30-day return policy, free returns on all orders",
  warranty: "2-year manufacturer warranty on all keyboards"
};

/* --- Render product cards into the DOM --- */
(function () {
  'use strict';

  function badgeClass(badge) {
    if (!badge) return '';
    var slug = badge.toLowerCase().replace(/\s+/g, '-');
    return 'product-card__badge--' + slug;
  }

  function formatPrice(price) {
    var parts = price.toFixed(2).split('.');
    return parts[0] + '<span style="font-size:0.55em;vertical-align:super;opacity:0.7">.' + parts[1] + '</span>';
  }

  function createCard(product) {
    var card = document.createElement('div');
    card.className = 'product-card';
    card.setAttribute('data-product-id', product.id);

    var badgeHTML = '';
    if (product.badge) {
      badgeHTML = '<span class="product-card__badge ' + badgeClass(product.badge) + '">' + product.badge + '</span>';
    }

    var featuresHTML = product.features.map(function (f) {
      return '<li>' + f + '</li>';
    }).join('');

    var cartIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>' +
      '<path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>' +
      '</svg>';

    card.innerHTML =
      badgeHTML +
      '<h3 class="product-card__name">' + product.name + '</h3>' +
      '<div class="product-card__price">' + formatPrice(product.price) + '</div>' +
      '<div class="product-card__meta">' +
        '<span>' +
          '<svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="20" height="12" rx="2"/><path d="M12 12h.01"/></svg>' +
          product.switches +
        '</span>' +
        '<span>' +
          '<svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.55a11 11 0 0 1 14 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><circle cx="12" cy="20" r="1"/></svg>' +
          product.connectivity +
        '</span>' +
      '</div>' +
      '<ul class="product-card__features">' + featuresHTML + '</ul>' +
      '<div class="product-card__actions">' +
        '<button class="btn-cart" data-product-id="' + product.id + '">' +
          cartIcon + ' Add to Cart' +
        '</button>' +
      '</div>';

    return card;
  }

  function render() {
    var grid = document.getElementById('products-grid');
    if (!grid) return;

    var fragment = document.createDocumentFragment();
    window.PRODUCTS.forEach(function (product) {
      fragment.appendChild(createCard(product));
    });
    grid.appendChild(fragment);
  }

  /* Run when DOM is ready */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();
