
const adminMessage = document.getElementById("admin-message");
const productFormPanel = document.getElementById("product-form-panel");
const productForm = document.getElementById("product-form");
const productList = document.getElementById("admin-product-list");

const productIdInput = document.getElementById("product-id");
const productNameInput = document.getElementById("product-name");
const productPriceInput = document.getElementById("product-price");
const productStockInput = document.getElementById("product-stock");
const productImageKeyInput = document.getElementById("product-image-key");
const productDescriptionInput = document.getElementById("product-description");

const newProductButton = document.getElementById("new-product-button");
const cancelFormButton = document.getElementById("cancel-form-button");
const reloadProductsButton = document.getElementById("reload-products-button");
const saveProductButton = document.getElementById("save-product-button");
const formTitle = document.getElementById("form-title");

document.getElementById("admin-current-year").textContent =
    new Date().getFullYear();

function showAdminMessage(message, type = "") {
    adminMessage.textContent = message;
    adminMessage.className = `notice ${type}`.trim();
    adminMessage.classList.remove("hidden");
}

function hideAdminMessage() {
    adminMessage.textContent = "";
    adminMessage.className = "notice hidden";
}

function formatAdminPrice(price) {
    const amount = Number(price);

    if (!Number.isFinite(amount)) {
        return String(price ?? "N/A");
    }

    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
    }).format(amount);
}

function addCell(row, value) {
    const cell = document.createElement("td");
    cell.textContent = value ?? "—";
    row.appendChild(cell);
    return cell;
}

function resetProductForm() {
    productForm.reset();
    productIdInput.value = "";
    productStockInput.value = "0";
    formTitle.textContent = "Add a Product";
    saveProductButton.textContent = "Save Product";
}

function openNewProductForm() {
    resetProductForm();
    productFormPanel.classList.remove("hidden");
    productNameInput.focus();
}

function closeProductForm() {
    productFormPanel.classList.add("hidden");
    resetProductForm();
}

function openEditProductForm(product) {
    productIdInput.value = product.product_id;
    productNameInput.value = product.name ?? "";
    productPriceInput.value = product.price ?? "";
    productStockInput.value = product.stock_quantity ?? 0;
    productImageKeyInput.value = product.image_key ?? "";
    productDescriptionInput.value = product.description ?? "";

    formTitle.textContent = "Edit Product";
    saveProductButton.textContent = "Update Product";
    productFormPanel.classList.remove("hidden");
    productFormPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    productNameInput.focus();
}

async function loadAdminProducts() {
    productList.replaceChildren();

    const loadingRow = document.createElement("tr");
    const loadingCell = document.createElement("td");
    loadingCell.colSpan = 5;
    loadingCell.textContent = "Loading products...";
    loadingRow.appendChild(loadingCell);
    productList.appendChild(loadingRow);

    reloadProductsButton.disabled = true;
    hideAdminMessage();

    try {
        const products = await CloudCartAPI.getProducts();
        productList.replaceChildren();

        if (!Array.isArray(products) || products.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 5;
            cell.className = "empty-state";
            cell.textContent = "No products found. Add your first product.";
            row.appendChild(cell);
            productList.appendChild(row);
            return;
        }

        products.forEach((product) => {
            const row = document.createElement("tr");

            addCell(row, product.product_id);
            addCell(row, product.name);
            addCell(row, formatAdminPrice(product.price));
            addCell(row, product.stock_quantity ?? 0);

            const actionsCell = document.createElement("td");
            const actions = document.createElement("div");
            actions.className = "table-actions";

            const editButton = document.createElement("button");
            editButton.type = "button";
            editButton.className = "btn btn-secondary";
            editButton.textContent = "Edit";
            editButton.addEventListener("click", () => {
                openEditProductForm(product);
            });

            const deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.className = "btn btn-danger";
            deleteButton.textContent = "Delete";
            deleteButton.addEventListener("click", async () => {
                const confirmed = window.confirm(
                    `Delete "${product.name}"? This action cannot be undone.`
                );

                if (!confirmed) {
                    return;
                }

                deleteButton.disabled = true;

                try {
                    await CloudCartAPI.deleteProduct(product.product_id);
                    showAdminMessage("Product deleted successfully.", "success");
                    await loadAdminProducts();
                } catch (error) {
                    showAdminMessage(
                        `Could not delete product: ${error.message}`,
                        "error"
                    );
                    deleteButton.disabled = false;
                }
            });

            actions.append(editButton, deleteButton);
            actionsCell.appendChild(actions);
            row.appendChild(actionsCell);
            productList.appendChild(row);
        });
    } catch (error) {
        productList.replaceChildren();

        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 5;
        cell.textContent = "Could not load products. Check the backend connection.";
        row.appendChild(cell);
        productList.appendChild(row);

        showAdminMessage(`API error: ${error.message}`, "error");
    } finally {
        reloadProductsButton.disabled = false;
    }
}

productForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAdminMessage();

    const product = {
        name: productNameInput.value.trim(),
        description: productDescriptionInput.value.trim() || null,
        price: Number(productPriceInput.value),
        stock_quantity: Number(productStockInput.value),
        image_key: productImageKeyInput.value.trim() || null,
    };

    if (!product.name) {
        showAdminMessage("Please enter a product name.", "error");
        return;
    }

    if (!Number.isFinite(product.price) || product.price < 0) {
        showAdminMessage("Price must be a valid non-negative number.", "error");
        return;
    }

    if (
        !Number.isInteger(product.stock_quantity) ||
        product.stock_quantity < 0
    ) {
        showAdminMessage("Stock must be a non-negative whole number.", "error");
        return;
    }

    saveProductButton.disabled = true;

    try {
        const existingId = productIdInput.value;

        if (existingId) {
            await CloudCartAPI.updateProduct(existingId, product);
            showAdminMessage("Product updated successfully.", "success");
        } else {
            await CloudCartAPI.createProduct(product);
            showAdminMessage("Product created successfully.", "success");
        }

        closeProductForm();
        await loadAdminProducts();
    } catch (error) {
        showAdminMessage(`Could not save product: ${error.message}`, "error");
    } finally {
        saveProductButton.disabled = false;
    }
});

newProductButton.addEventListener("click", openNewProductForm);
cancelFormButton.addEventListener("click", closeProductForm);
reloadProductsButton.addEventListener("click", loadAdminProducts);

loadAdminProducts();
