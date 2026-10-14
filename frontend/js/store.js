
const productGrid = document.getElementById("product-grid");
const storeMessage = document.getElementById("store-message");
const refreshButton = document.getElementById("refresh-button");
const currentYear = document.getElementById("current-year");

if (currentYear) {
    currentYear.textContent = new Date().getFullYear();
}

function showStoreMessage(message, type = "") {
    storeMessage.textContent = message;
    storeMessage.className = `notice ${type}`.trim();
    storeMessage.classList.remove("hidden");
}

function hideStoreMessage() {
    storeMessage.textContent = "";
    storeMessage.className = "notice hidden";
}

function formatPrice(price) {
    const amount = Number(price);

    if (!Number.isFinite(amount)) {
        return String(price ?? "Price unavailable");
    }

    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
    }).format(amount);
}

function createProductCard(product) {
    const card = document.createElement("article");
    card.className = "product-card";

    const imageContainer = document.createElement("div");
    imageContainer.className = "product-image";

    // The API currently provides image_key, not necessarily a public image URL.
    // Use a placeholder until image delivery is implemented.
    imageContainer.textContent = "🛍️";

    const info = document.createElement("div");
    info.className = "product-info";

    const name = document.createElement("h3");
    name.textContent = product.name || "Unnamed product";

    const description = document.createElement("p");
    description.textContent =
        product.description || "A great addition to your everyday essentials.";

    const bottom = document.createElement("div");
    bottom.className = "product-bottom";

    const price = document.createElement("span");
    price.className = "price";
    price.textContent = formatPrice(product.price);

    const stock = document.createElement("span");
    const quantity = Number(product.stock_quantity ?? 0);
    stock.className = quantity > 0 ? "stock" : "stock out";
    stock.textContent = quantity > 0 ? "In stock" : "Out of stock";

    bottom.append(price, stock);
    info.append(name, description, bottom);
    card.append(imageContainer, info);

    return card;
}

async function loadProducts() {
    productGrid.replaceChildren();

    const loading = document.createElement("p");
    loading.className = "muted";
    loading.textContent = "Loading products...";
    productGrid.appendChild(loading);

    refreshButton.disabled = true;
    hideStoreMessage();

    try {
        const products = await CloudCartAPI.getProducts();

        productGrid.replaceChildren();

        if (!Array.isArray(products) || products.length === 0) {
            const empty = document.createElement("div");
            empty.className = "empty-state";
            empty.textContent = "No products available yet. Please check back soon.";
            productGrid.appendChild(empty);
            return;
        }

        products.forEach((product) => {
            productGrid.appendChild(createProductCard(product));
        });
    } catch (error) {
        productGrid.replaceChildren();
        showStoreMessage(
            `Could not load products: ${error.message}. Check that the backend is running.`,
            "error"
        );

        const retry = document.createElement("button");
        retry.className = "btn btn-primary";
        retry.textContent = "Try Again";
        retry.addEventListener("click", loadProducts);
        productGrid.appendChild(retry);
    } finally {
        refreshButton.disabled = false;
    }
}

refreshButton.addEventListener("click", loadProducts);

loadProducts();
