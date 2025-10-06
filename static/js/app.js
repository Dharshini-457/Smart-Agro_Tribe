// static/js/app.js
// This file is used by all templates. It detects page by looking for DOM elements.

async function api(url, method = 'GET', body = null) {
  const options = { method, headers: {} };
  if (body) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  const res = await fetch(url, options);
  return res.json();
}

/* ---------- Login/Register (login.html) ---------- */
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
if (loginForm) {
  document.getElementById('showRegister').addEventListener('click', () => {
    loginForm.classList.add('hidden');
    registerForm.classList.remove('hidden');
  });
  document.getElementById('hideRegister').addEventListener('click', () => {
    registerForm.classList.add('hidden');
    loginForm.classList.remove('hidden');
  });

  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const role = document.getElementById('role').value;
    const res = await api('/api/login', 'POST', { email, password });
    const msg = document.getElementById('message');
    if (res.ok) {
      // redirect based on role
      if (res.role === 'farmer') window.location = '/farmer';
      else window.location = '/buyer';
    } else {
      msg.textContent = res.error || 'Login failed';
      setTimeout(() => (msg.textContent = ''), 3000);
    }
  });

  document.getElementById('doRegister').addEventListener('click', async () => {
    const name = document.getElementById('r_name').value.trim();
    const email = document.getElementById('r_email').value.trim();
    const password = document.getElementById('r_password').value;
    const role = document.getElementById('r_role').value;
    const res = await api('/api/register', 'POST', { name, email, password, role });
    const msg = document.getElementById('message');
    if (res.ok) {
      msg.style.color = 'green';
      msg.textContent = 'Registered. You can login now.';
      setTimeout(() => {
        msg.textContent = '';
        registerForm.classList.add('hidden');
        loginForm.classList.remove('hidden');
      }, 1500);
    } else {
      msg.textContent = res.error || 'Registration failed';
    }
  });
}

/* ---------- Farmer Dashboard JS ---------- */
const addProductBtn = document.getElementById('addProductBtn');
if (addProductBtn) {
  // Add product
  addProductBtn.addEventListener('click', async () => {
    // For prototype, ask farmer email (or use session later)
    const farmerEmail = prompt('Enter your email used to register (for demo):');
    if (!farmerEmail) return alert('Email required');

    const product = document.getElementById('p_name').value.trim();
    const category = document.getElementById('p_category').value.trim();
    const quality = document.getElementById('p_quality').value.trim();
    const masp = parseFloat(document.getElementById('p_masp').value);
    const available = parseInt(document.getElementById('p_qty').value);

    if (!product || !masp || !available) return alert('Please enter product, masp and qty');

    const res = await api('/api/products', 'POST', {
      farmer_email: farmerEmail,
      name: product,
      category,
      quality,
      masp,
      available
    });
    if (res.ok) {
      document.getElementById('addMsg').classList.remove('hidden');
      setTimeout(() => document.getElementById('addMsg').classList.add('hidden'), 1200);
      loadFarmerData(farmerEmail);
    } else {
      alert(res.error || 'Failed to add product');
    }
  });

  async function loadFarmerData(email) {
    const res = await api(/api/farmer/${encodeURIComponent(email)}/products);
    const myProducts = document.getElementById('myProducts');
    const myOrders = document.getElementById('myOrders');
    myProducts.innerHTML = '';
    myOrders.innerHTML = '';
    if (res.products) {
      res.products.forEach(p => {
        const el = document.createElement('div');
        el.className = 'border p-2 rounded';
        el.innerHTML = <b>${p.name}</b> | MASP: ₹${p.masp} | Available: ${p.available};
        myProducts.appendChild(el);
      });
    }
    if (res.orders) {
      res.orders.forEach(o => {
        const el = document.createElement('div');
        el.className = 'border p-2 rounded';
        el.innerHTML = <b>#${o.id}</b> ${o.product_name} x${o.qty} | ₹${o.total_price} | ${o.status};
        myOrders.appendChild(el);
      });
    }
  }

  // initial ask to load farmer data (demo)
  const farmerEmailPrompt = async () => {
    const email = prompt('Enter your registered farmer email to load your data (demo):');
    if (email) loadFarmerData(email);
  };
  setTimeout(farmerEmailPrompt, 300);
}

/* ---------- Buyer Dashboard JS ---------- */
const refreshProductsBtn = document.getElementById('refreshProducts');
if (refreshProductsBtn) {
  async function loadProducts() {
    const products = await api('/api/products', 'GET');
    const grid = document.getElementById('productGrid');
    grid.innerHTML = '';
    products.forEach(p => {
      const card = document.createElement('div');
      card.className = 'bg-white p-4 rounded shadow';
      card.innerHTML = `
        <div class="flex justify-between items-start">
          <div>
            <h3 class="font-bold">${p.name}</h3>
            <p class="text-sm text-gray-600">Farmer: ${p.farmer_email}</p>
            <p class="text-sm">Quality: ${p.quality}</p>
          </div>
          <div class="text-right">
            <p class="text-lg font-bold text-green-600">₹${p.current_price}</p>
            <p class="text-xs text-gray-500">MASP: ₹${p.masp}</p>
            <p class="text-xs">${p.pricing_breakdown.recommendation}</p>
          </div>
        </div>
        <div class="mt-3 flex space-x-2">
          <button class="bg-blue-600 text-white px-3 py-1 rounded" onclick="prefillOrder(${p.id})">Quick Buy</button>
        </div>
      `;
      grid.appendChild(card);
    });
  }

  window.prefillOrder = function(productId) {
    document.getElementById('order_product_id').value = productId;
  };

  document.getElementById('placeOrderBtn').addEventListener('click', async () => {
    const buyer_name = document.getElementById('order_name').value.trim();
    const buyer_email = document.getElementById('order_email').value.trim();
    const product_id = parseInt(document.getElementById('order_product_id').value);
    const qty = parseInt(document.getElementById('order_qty').value);

    if (!buyer_name || !buyer_email || !product_id || !qty) return alert('Fill order details');

    const res = await api('/api/orders', 'POST', {
      buyer_name, buyer_email, product_id, qty
    });
    if (res.ok) {
      document.getElementById('orderMsg').classList.remove('hidden');
      setTimeout(() => document.getElementById('orderMsg').classList.add('hidden'), 1200);
      loadProducts();
    } else {
      alert(res.error || 'Order failed');
    }
  });

  document.getElementById('refreshProducts').addEventListener('click', loadProducts);
  // initial load
  setTimeout(loadProducts, 200);
}

/* ---------- Logout button used on dashboards ---------- */
const logoutBtn = document.querySelectorAll('#logoutBtn');
if (logoutBtn) {
  logoutBtn.forEach(btn => {
    btn.addEventListener('click', async () => {
      await api('/api/logout', 'POST');
      window.location = '/';
    });
  });
}