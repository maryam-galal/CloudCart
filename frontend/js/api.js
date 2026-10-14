
const API_BASE_URL = "http://127.0.0.1:8000";

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...options.headers,
        },
    });

    if (response.status === 204) {
        return null;
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) {
        const detail = data?.detail;
        const message =
            typeof detail === "string"
                ? detail
                : detail
                    ? JSON.stringify(detail)
                    : `Request failed with status ${response.status}`;

        throw new Error(message);
    }

    return data;
}

const CloudCartAPI = {
    getProducts() {
        return apiRequest("/api/products");
    },

    getProduct(productId) {
        return apiRequest(`/api/products/${productId}`);
    },

    createProduct(product) {
        return apiRequest("/api/products", {
            method: "POST",
            body: JSON.stringify(product),
        });
    },

    updateProduct(productId, product) {
        return apiRequest(`/api/products/${productId}`, {
            method: "PUT",
            body: JSON.stringify(product),
        });
    },

    deleteProduct(productId) {
        return apiRequest(`/api/products/${productId}`, {
            method: "DELETE",
        });
    },

    signup(user) {
        return apiRequest("/api/auth/signup", {
            method: "POST",
            body: JSON.stringify(user),
        });
    },

    login(credentials) {
        return apiRequest("/api/auth/login", {
            method: "POST",
            body: JSON.stringify(credentials),
        });
    },
};
